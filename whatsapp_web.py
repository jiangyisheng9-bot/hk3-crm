"""
WhatsApp Web integration via Playwright (headless Chromium).
Runs a single browser session in a dedicated worker thread,
exposes a thread-safe API to the Flask app.

⚠️  This is a best-effort scrape of web.whatsapp.com.
    DOM selectors and login flow may break when WhatsApp updates its UI.
"""
import os
import re
import time
import base64
import threading
import queue
import traceback
from datetime import datetime

# Playwright is imported lazily inside the worker thread so the Flask app
# can still boot if Playwright isn't installed yet.

WA_URL = 'https://web.whatsapp.com/'
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wa_session')

# ─── Public state ─────────────────────────────────────────────
# state values:
#   stopped     – worker thread not running
#   starting    – Playwright launching
#   waiting_qr  – QR code visible, waiting for phone scan
#   loading     – scanned, WhatsApp is syncing
#   ready       – chat list visible, fully logged in
#   expired     – QR expired; click refresh
#   error       – fatal error; check `last_error`

_state = {
    'status': 'stopped',
    'qr_dataurl': None,        # data:image/png;base64,...
    'last_error': None,
    'updated_at': None,
}
_state_lock = threading.Lock()

# Worker plumbing
_cmd_queue: 'queue.Queue[tuple]' = queue.Queue()
_worker_thread = None
_worker_started = False
_worker_lock = threading.Lock()


def _set_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)
        _state['updated_at'] = datetime.utcnow().isoformat()


def get_state() -> dict:
    with _state_lock:
        return dict(_state)


# ─── Public API (thread-safe, called from Flask) ───────────────

def ensure_worker():
    """Spawn the worker thread once."""
    global _worker_thread, _worker_started
    with _worker_lock:
        if _worker_started and _worker_thread and _worker_thread.is_alive():
            return
        _worker_started = True
        _worker_thread = threading.Thread(target=_worker_main, name='wa-web-worker', daemon=True)
        _worker_thread.start()


def request_start():
    """Ask worker to (re)open WhatsApp Web."""
    ensure_worker()
    _cmd_queue.put(('start', None))


def request_refresh_qr():
    ensure_worker()
    _cmd_queue.put(('refresh_qr', None))


def request_send(phone: str, text: str, reply_q: 'queue.Queue' = None):
    ensure_worker()
    _cmd_queue.put(('send', (phone, text, reply_q)))


def send_sync(phone: str, text: str, timeout: int = 30) -> dict:
    """Synchronous send — blocks until worker responds."""
    rq: queue.Queue = queue.Queue()
    request_send(phone, text, rq)
    try:
        return rq.get(timeout=timeout)
    except queue.Empty:
        return {'ok': False, 'error': 'send timeout'}


def request_poll_messages(reply_q: 'queue.Queue' = None):
    ensure_worker()
    _cmd_queue.put(('poll', reply_q))


def poll_messages_sync(timeout: int = 20) -> list:
    rq: queue.Queue = queue.Queue()
    request_poll_messages(rq)
    try:
        return rq.get(timeout=timeout)
    except queue.Empty:
        return []


def request_stop():
    _cmd_queue.put(('stop', None))


# ─── Worker (single thread, owns the browser) ─────────────────

class _Worker:
    def __init__(self):
        self.pw = None
        self.context = None
        self.page = None
        self.last_seen_msgs = {}  # chat_id -> last timestamp string

    def boot(self):
        from playwright.sync_api import sync_playwright
        _set_state(status='starting', last_error=None)
        os.makedirs(PROFILE_DIR, exist_ok=True)
        self.pw = sync_playwright().start()
        # Persistent context => session cookies survive restarts.
        self.context = self.pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=True,
            args=['--disable-blink-features=AutomationControlled'],
            user_agent=('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/131.0.0.0 Safari/537.36'),
            viewport={'width': 1280, 'height': 900},
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto(WA_URL, wait_until='domcontentloaded', timeout=60000)

    def shutdown(self):
        try:
            if self.context: self.context.close()
        except Exception:
            pass
        try:
            if self.pw: self.pw.stop()
        except Exception:
            pass
        self.context = self.pw = self.page = None
        _set_state(status='stopped', qr_dataurl=None)

    # ─── status detection ─────────────────────────────────

    def detect_status(self) -> str:
        """Return one of: waiting_qr, loading, ready, expired, error."""
        if not self.page:
            return 'error'
        try:
            # 1) chat pane visible -> ready
            pane = self.page.locator('div#pane-side, div[aria-label="聊天列表"], div[aria-label="Chat list"]')
            if pane.count() > 0 and pane.first.is_visible():
                return 'ready'

            # 2) QR canvas
            qr = self.page.locator('canvas[aria-label*="Scan"], canvas[aria-label*="扫"], div[data-ref] canvas')
            if qr.count() > 0 and qr.first.is_visible():
                return 'waiting_qr'

            # 3) "Click to reload QR code" / expired
            expired = self.page.get_by_text(re.compile(r'(Click to reload|重新加载|过期|expired)', re.I))
            if expired.count() > 0:
                return 'expired'

            # 4) "Loading your chats" intermediate state
            loading = self.page.get_by_text(re.compile(r'(Loading|正在加载|Syncing|同步)', re.I))
            if loading.count() > 0:
                return 'loading'
        except Exception:
            return 'error'
        return 'loading'

    def grab_qr(self):
        """Screenshot the QR canvas and store as data URL."""
        try:
            qr = self.page.locator('canvas[aria-label*="Scan"], canvas[aria-label*="扫"], div[data-ref] canvas').first
            if qr.count() == 0 or not qr.is_visible():
                return None
            png = qr.screenshot(timeout=5000)
            return 'data:image/png;base64,' + base64.b64encode(png).decode('ascii')
        except Exception:
            return None

    def refresh_loop_step(self):
        """Update state once."""
        st = self.detect_status()
        update = {'status': st}
        if st == 'waiting_qr':
            qr = self.grab_qr()
            if qr:
                update['qr_dataurl'] = qr
        elif st == 'ready':
            update['qr_dataurl'] = None
        elif st == 'expired':
            update['qr_dataurl'] = None
            # try clicking the reload button
            try:
                btn = self.page.get_by_role('button', name=re.compile(r'(reload|重新)', re.I))
                if btn.count() > 0:
                    btn.first.click(timeout=3000)
            except Exception:
                pass
        _set_state(**update)

    # ─── send message ────────────────────────────────────

    def send(self, phone: str, text: str) -> dict:
        if self.detect_status() != 'ready':
            return {'ok': False, 'error': 'WhatsApp Web 尚未登录（请先扫码）'}
        digits = re.sub(r'\D', '', phone or '')
        if not digits:
            return {'ok': False, 'error': '号码无效'}
        # Use wa.me deep link (within already-logged-in session).
        try:
            url = f'https://web.whatsapp.com/send?phone={digits}&text={text}'
            # Don't actually preload text via URL (browser drops it sometimes).
            self.page.goto(f'https://web.whatsapp.com/send?phone={digits}',
                           wait_until='domcontentloaded', timeout=30000)
            # Wait for chat input
            box = self.page.locator('div[contenteditable="true"][data-tab="10"], '
                                    'div[contenteditable="true"][role="textbox"]').last
            box.wait_for(state='visible', timeout=20000)
            box.click()
            self.page.keyboard.type(text, delay=15)
            self.page.keyboard.press('Enter')
            time.sleep(1.0)
            return {'ok': True, 'sent_at': datetime.utcnow().isoformat()}
        except Exception as e:
            return {'ok': False, 'error': f'发送失败: {e}'}

    # ─── poll incoming messages ──────────────────────────

    def poll_messages(self) -> list:
        """Return list of {phone, name, text, timestamp} for unread chats.
        Best effort — opens each unread chat, reads visible incoming msgs."""
        if self.detect_status() != 'ready':
            return []
        out = []
        try:
            # Unread chats have a span with an unread count.
            chats = self.page.locator('div#pane-side div[role="listitem"]').all()[:30]
            for chat in chats:
                try:
                    unread = chat.locator('span[aria-label*="unread"], span[aria-label*="未读"]')
                    if unread.count() == 0:
                        continue
                    name_el = chat.locator('span[dir="auto"][title]').first
                    name = name_el.get_attribute('title') if name_el.count() else None
                    chat.click(timeout=3000)
                    self.page.wait_for_timeout(800)
                    # Read the visible incoming message bubbles
                    bubbles = self.page.locator('div.message-in span.selectable-text').all()[-5:]
                    texts = [b.inner_text() for b in bubbles if b.inner_text().strip()]
                    # Try to extract phone via header link
                    phone = None
                    try:
                        header = self.page.locator('header span[title]').first
                        title = header.get_attribute('title') if header.count() else ''
                        m = re.search(r'(\+?\d[\d\s\-]{6,})', title or '')
                        if m: phone = re.sub(r'\D', '', m.group(1))
                    except Exception:
                        pass
                    for t in texts:
                        out.append({
                            'name': name,
                            'phone': phone,
                            'text': t,
                            'timestamp': datetime.utcnow().isoformat(),
                        })
                except Exception:
                    continue
        except Exception:
            pass
        return out


def _worker_main():
    """Long-lived worker: owns the Playwright browser, drains the cmd queue,
    and periodically refreshes status."""
    w = _Worker()
    last_refresh = 0
    try:
        while True:
            try:
                cmd, payload = _cmd_queue.get(timeout=2.0)
            except queue.Empty:
                cmd, payload = (None, None)

            try:
                if cmd == 'start':
                    if not w.context:
                        w.boot()
                elif cmd == 'refresh_qr':
                    if not w.context:
                        w.boot()
                    else:
                        try:
                            w.page.reload(wait_until='domcontentloaded', timeout=30000)
                        except Exception:
                            pass
                elif cmd == 'send':
                    phone, text, rq = payload
                    if not w.context: w.boot()
                    res = w.send(phone, text)
                    if rq is not None:
                        rq.put(res)
                elif cmd == 'poll':
                    rq = payload
                    if not w.context:
                        if rq is not None: rq.put([])
                    else:
                        msgs = w.poll_messages()
                        if rq is not None: rq.put(msgs)
                elif cmd == 'stop':
                    w.shutdown()
                    return
            except Exception as e:
                _set_state(status='error', last_error=f'{e}\n{traceback.format_exc()[-500:]}')

            # Periodic refresh of status / QR
            if w.context and time.time() - last_refresh > 3.0:
                try:
                    w.refresh_loop_step()
                except Exception as e:
                    _set_state(last_error=str(e))
                last_refresh = time.time()
    finally:
        w.shutdown()
