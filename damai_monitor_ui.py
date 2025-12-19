import os
import time
import threading
import queue
import pickle
import webbrowser
import customtkinter as ctk

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# --------------------
# 重要说明
# --------------------
# 该程序仅做“监控/提醒/辅助打开页面”，不包含自动下单、自动付款、绕过风控等功能。
# 抢票/刷票/绕过反爬可能违反平台规则甚至触法，请务必合规使用。


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


COOKIE_FILE = "damai_cookies.pkl"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

PURCHASABLE_KEYWORDS = ["立即", "购票", "购买", "选座", "去支付", "立即付款", "确认付款"]
NOT_PURCHASABLE_KEYWORDS = ["缺货", "无票", "登记", "缺货登记", "提交缺货登记"]


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class MonitorTask:
    url: str
    session_keyword: str = ""
    price_keyword: str = ""
    handle: Optional[str] = None
    last_state: Optional[str] = None


class DamaiBrowserSession:
    """浏览器会话：支持打开登录页、(可选)绑定已有 Chrome、保存/加载 cookies。"""

    def __init__(
        self,
        log_queue: "queue.Queue[str]",
        cookie_file: str = COOKIE_FILE,
    ):
        self.log_queue = log_queue
        self.cookie_file = cookie_file

        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _log(self, msg: str) -> None:
        self.log_queue.put(f"[{now_ts()}] [浏览器] {msg}")

    def setup_driver(self) -> bool:
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--start-maximized")
            options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")
            # 不做任何反爬绕过注入；只做基础可用性设置。

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(0)
            self.wait = WebDriverWait(self.driver, 5)
            self._log("Chrome 启动成功")
            return True
        except Exception as e:
            self._log(f"启动浏览器失败：{str(e)[:200]}")
            return False

    def attach_existing(self, debugger_address: str = "127.0.0.1:9222") -> bool:
        """绑定已打开的 Chrome（需要你自己用 --remote-debugging-port 启动）"""
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", debugger_address)
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(0)
            self.wait = WebDriverWait(self.driver, 5)
            _ = self.driver.current_url
            self._log(f"绑定成功：{debugger_address}")
            return True
        except Exception as e:
            self._log(f"绑定失败：{str(e)[:200]}")
            return False

    def open_login_page(self) -> bool:
        if not self.driver and not self.setup_driver():
            return False

        try:
            assert self.driver is not None
            self._log("正在打开大麦首页...")
            self.driver.get("https://www.damai.cn/")
            time.sleep(0.8)
            self._log("正在打开登录页...请在浏览器中扫码登录")
            self.driver.get("https://passport.damai.cn/login?ru=https://www.damai.cn/")
            return True
        except Exception as e:
            self._log(f"打开登录页失败：{str(e)[:200]}")
            return False

    def confirm_login_and_save_cookies(self) -> bool:
        if not self.driver:
            self._log("浏览器未启动")
            return False

        try:
            self._log("正在验证登录状态...")
            self.driver.get("https://www.damai.cn/")
            time.sleep(0.8)
            page = self.driver.page_source or ""
            # 只是弱校验：页面包含常见登录标识就认为成功
            if any(k in page for k in ["我的大麦", "个人中心", "退出"]):
                self._save_cookies()
                self._log("登录状态：已检测到登录标识")
                return True

            # 退一步：不在登录域名也允许继续（有时页面结构变动）
            if "passport.damai.cn" not in (self.driver.current_url or ""):
                self._save_cookies()
                self._log("登录状态：未强校验但已离开登录域名，允许继续")
                return True

            self._log("未能确认登录，请确认已扫码并完成登录")
            return False
        except Exception as e:
            self._log(f"确认登录失败：{str(e)[:200]}")
            return False

    def _save_cookies(self) -> None:
        if not self.driver:
            return
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            self._log(f"Cookie 已保存：{self.cookie_file}")
        except Exception as e:
            self._log(f"Cookie 保存失败：{str(e)[:200]}")

    def load_cookies(self) -> bool:
        if not self.driver and not self.setup_driver():
            return False
        if not os.path.exists(self.cookie_file):
            self._log("Cookie 文件不存在")
            return False

        try:
            assert self.driver is not None
            self.driver.get("https://www.damai.cn/")
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for c in cookies:
                try:
                    self.driver.add_cookie(c)
                except Exception:
                    # 个别 cookie 可能因域/字段问题添加失败，忽略
                    pass
            self.driver.refresh()
            self._log("Cookie 已加载并刷新")
            return True
        except Exception as e:
            self._log(f"加载 Cookie 失败：{str(e)[:200]}")
            return False

    def close(self) -> None:
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None
        self.wait = None


class DamaiTabMonitor:
    """多标签页轮询监控：检测是否出现可购买按钮文本，发现则提醒并切到对应标签页。"""

    def __init__(
        self,
        driver: webdriver.Chrome,
        log_queue: "queue.Queue[str]",
        event_queue: "queue.Queue[dict]",
        stop_event: threading.Event,
        pause_event: threading.Event,
        refresh_seconds: float,
    ):
        self.driver = driver
        self.log_queue = log_queue
        self.event_queue = event_queue
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.refresh_seconds = refresh_seconds
        self.tasks: List[MonitorTask] = []

    def _log(self, msg: str) -> None:
        self.log_queue.put(f"[{now_ts()}] [监控] {msg}")

    def _emit(self, **payload) -> None:
        self.event_queue.put(payload)

    def prepare_tabs(self, tasks: List[MonitorTask]) -> None:
        self.tasks = []
        base = self.driver.current_window_handle

        for idx, t in enumerate(tasks, start=1):
            url = t.url.strip()
            if not url:
                continue
            self.driver.switch_to.window(base)
            self.driver.execute_script("window.open(arguments[0], '_blank');", url)
            handle = self.driver.window_handles[-1]
            self.driver.switch_to.window(handle)
            self._log(f"已打开标签页#{idx}: {url}")
            self.tasks.append(
                MonitorTask(
                    url=url,
                    session_keyword=t.session_keyword,
                    price_keyword=t.price_keyword,
                    handle=handle,
                    last_state=None,
                )
            )

    def _try_select_by_keyword(self, css_selector: str, keyword: str) -> None:
        if not keyword:
            return
        try:
            els = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            for el in els:
                if keyword in (el.text or ""):
                    el.click()
                    break
        except Exception:
            pass

    def _detect_state_text(self) -> Optional[str]:
        """尽量宽松地从页面上提取“购买/选座/支付”等按钮文本。"""
        selectors = [
            ".buybtn",
            "button",
            "a",
        ]
        try:
            for sel in selectors:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:80]:
                    if not el.is_displayed():
                        continue
                    txt = (el.text or "").strip()
                    if not txt:
                        continue
                    if any(k in txt for k in PURCHASABLE_KEYWORDS + NOT_PURCHASABLE_KEYWORDS):
                        return txt
            return None
        except Exception:
            return None

    def focus_task_tab(self, task_index_1based: int) -> None:
        if task_index_1based <= 0 or task_index_1based > len(self.tasks):
            return
        t = self.tasks[task_index_1based - 1]
        if not t.handle:
            return
        try:
            self.driver.switch_to.window(t.handle)
        except Exception:
            return

    def run(self) -> None:
        self._log(f"开始监控：任务数={len(self.tasks)}，刷新间隔={self.refresh_seconds:.2f}s")

        while not self.stop_event.is_set():
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.1)

            for idx, task in enumerate(self.tasks, start=1):
                if self.stop_event.is_set():
                    break
                if not task.handle:
                    continue

                try:
                    self.driver.switch_to.window(task.handle)
                except Exception:
                    continue

                try:
                    # 温和刷新：不要毫秒级狂刷，避免浏览器/网络/平台异常
                    self.driver.refresh()

                    # 尝试按关键词预选（如果页面结构匹配）
                    self._try_select_by_keyword(".sku-times-list .sku-times-item", task.session_keyword)
                    self._try_select_by_keyword(".sku-ticket-list .sku-ticket-item", task.price_keyword)

                    state_text = self._detect_state_text()
                    if state_text and state_text != task.last_state:
                        task.last_state = state_text
                        self._log(f"标签页#{idx} 状态变化：{state_text}")

                    if state_text and any(k in state_text for k in PURCHASABLE_KEYWORDS):
                        # 只提醒，不自动下单/付款
                        self._emit(type="purchasable_detected", task_index=idx, state_text=state_text, url=task.url)
                        # 置顶到该标签页，方便你手动操作
                        try:
                            self.driver.switch_to.window(task.handle)
                        except Exception:
                            pass

                except WebDriverException as e:
                    self._log(f"标签页#{idx} WebDriver异常：{str(e)[:120]}")
                except Exception as e:
                    self._log(f"标签页#{idx} 异常：{str(e)[:120]}")

                time.sleep(0.2)

            time.sleep(self.refresh_seconds)

        self._log("监控已停止（浏览器保持打开）")


class DamaiUI(ctk.CTk):
    """大麦监控提醒 UI（合规：监控/提醒/辅助打开，不自动下单）"""

    def __init__(self):
        super().__init__()

        self.title("大麦网监控提醒（合规版：不自动下单）")
        self.geometry("1100x900")
        self.minsize(900, 720)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.event_queue: "queue.Queue[dict]" = queue.Queue()

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        self.session = DamaiBrowserSession(self.log_queue)
        self.is_logged_in = False

        self.monitor: Optional[DamaiTabMonitor] = None
        self.monitor_thread: Optional[threading.Thread] = None

        self._build_widgets()
        self.after(30, self._poll_queues)

    def _build_widgets(self) -> None:
        # ---- 顶部说明 ----
        banner = ctk.CTkFrame(self)
        banner.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        banner.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            banner,
            text=(
                "提示：本工具仅用于监控/提醒/辅助打开页面，不提供自动下单/自动付款/绕过风控功能。"
            ),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # ---- 登录区 ----
        login_frame = ctk.CTkFrame(self)
        login_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        login_frame.grid_columnconfigure(6, weight=1)

        self.open_login_btn = ctk.CTkButton(login_frame, text="1. 打开登录页", command=self.open_login_page)
        self.open_login_btn.grid(row=0, column=0, padx=10, pady=10)

        self.confirm_login_btn = ctk.CTkButton(
            login_frame, text="2. 确认登录成功", command=self.confirm_login, state="disabled"
        )
        self.confirm_login_btn.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkButton(login_frame, text="从Cookie恢复(可选)", command=self.load_cookie_login).grid(
            row=0, column=2, padx=10, pady=10
        )

        ctk.CTkLabel(login_frame, text="(可选) 调试端口:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=3, padx=(10, 5), pady=10, sticky="e"
        )
        self.debugger_entry = ctk.CTkEntry(login_frame, width=160)
        self.debugger_entry.insert(0, "127.0.0.1:9222")
        self.debugger_entry.grid(row=0, column=4, padx=(0, 10), pady=10, sticky="w")

        ctk.CTkButton(login_frame, text="绑定已打开Chrome(可选)", command=self.attach_existing).grid(
            row=0, column=5, padx=10, pady=10
        )

        self.login_status = ctk.CTkLabel(login_frame, text="登录状态: 未登录", font=ctk.CTkFont(weight="bold"))
        self.login_status.grid(row=0, column=6, padx=10, pady=10, sticky="e")

        # ---- 任务区 ----
        config = ctk.CTkFrame(self)
        config.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        config.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            config,
            text="监控任务（每行一个）格式：链接 | 场次关键词 | 价格关键词",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")

        self.tasks_text = ctk.CTkTextbox(config, height=120, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.tasks_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.tasks_text.insert("end", "https://detail.damai.cn/item.htm?id=1000614198121 |  | \n")

        # ---- 刷新间隔 ----
        refresh = ctk.CTkFrame(self)
        refresh.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        refresh.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(refresh, text="刷新间隔（秒，建议 1-5）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w"
        )
        ctk.CTkLabel(refresh, text="间隔:").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self.refresh_entry = ctk.CTkEntry(refresh, width=120)
        self.refresh_entry.insert(0, "2")
        self.refresh_entry.grid(row=1, column=1, padx=(0, 10), pady=6, sticky="w")

        self.open_in_system_browser_btn = ctk.CTkButton(refresh, text="用系统浏览器打开首个链接", command=self.open_first_link)
        self.open_in_system_browser_btn.grid(row=1, column=2, padx=10, pady=6, sticky="w")

        # ---- 控制区 ----
        control = ctk.CTkFrame(self)
        control.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        control.grid_columnconfigure(4, weight=1)

        self.start_btn = ctk.CTkButton(control, text="开始监控", command=self.start_monitoring, state="disabled")
        self.start_btn.grid(row=0, column=0, padx=10, pady=10)

        self.pause_btn = ctk.CTkButton(control, text="暂停", command=self.pause_monitoring, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=10, pady=10)

        self.resume_btn = ctk.CTkButton(control, text="继续", command=self.resume_monitoring, state="disabled")
        self.resume_btn.grid(row=0, column=2, padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(control, text="停止", command=self.stop_monitoring, state="disabled", fg_color="red")
        self.stop_btn.grid(row=0, column=3, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(control, text="状态: 未开始", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=0, column=4, padx=10, pady=10, sticky="e")

        # ---- 提醒区 ----
        alert = ctk.CTkFrame(self)
        alert.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        alert.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(alert, text="提醒面板", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        self.alert_text = ctk.CTkTextbox(alert, height=110, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.alert_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # ---- 日志区 ----
        logf = ctk.CTkFrame(self)
        logf.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="nsew")
        logf.grid_columnconfigure(0, weight=1)
        logf.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(logf, text="运行日志", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        self.log_text = ctk.CTkTextbox(logf, wrap="word", font=ctk.CTkFont(family="Consolas", size=11))
        self.log_text.grid(row=1, column=0, padx=(10, 0), pady=(0, 10), sticky="nsew")
        sb = ctk.CTkScrollbar(logf, command=self.log_text.yview)
        sb.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="ns")
        self.log_text.configure(yscrollcommand=sb.set)

    def _append_log(self, msg: str) -> None:
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _append_alert(self, msg: str) -> None:
        self.alert_text.insert("end", msg + "\n")
        self.alert_text.see("end")

    def _set_status(self, s: str) -> None:
        self.status_label.configure(text=f"状态: {s}")

    def _set_login_status(self, s: str) -> None:
        self.login_status.configure(text=f"登录状态: {s}")

    def _get_refresh_seconds(self) -> Optional[float]:
        try:
            v = float(self.refresh_entry.get())
            # 合理范围：0.5s ~ 30s
            v = max(0.5, min(v, 30.0))
            return v
        except ValueError:
            self._append_log(f"[{now_ts()}] 刷新间隔必须是数字")
            return None

    @staticmethod
    def _parse_tasks(raw: str) -> List[MonitorTask]:
        tasks: List[MonitorTask] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            url = parts[0] if len(parts) > 0 else ""
            sess = parts[1] if len(parts) > 1 else ""
            price = parts[2] if len(parts) > 2 else ""
            if url:
                tasks.append(MonitorTask(url=url, session_keyword=sess, price_keyword=price))
        return tasks

    # ---------- UI Actions ----------
    def open_first_link(self) -> None:
        tasks = self._parse_tasks(self.tasks_text.get("1.0", "end").strip())
        if not tasks:
            self._append_log(f"[{now_ts()}] 未找到任务链接")
            return
        webbrowser.open(tasks[0].url)

    def open_login_page(self) -> None:
        self.open_login_btn.configure(state="disabled")
        self.confirm_login_btn.configure(state="disabled")
        self._set_login_status("打开登录页中...")

        def run():
            ok = self.session.open_login_page()
            self.after(0, lambda: self._after_open_login(ok))

        threading.Thread(target=run, daemon=True).start()

    def _after_open_login(self, ok: bool) -> None:
        if ok:
            self._set_login_status("请扫码登录")
            self.confirm_login_btn.configure(state="normal")
        else:
            self._set_login_status("打开失败")
            self.open_login_btn.configure(state="normal")

    def attach_existing(self) -> None:
        self._set_login_status("绑定中...")
        addr = (self.debugger_entry.get() or "").strip() or "127.0.0.1:9222"

        def run():
            ok = self.session.attach_existing(addr)
            self.after(0, lambda: self._after_attach(ok))

        threading.Thread(target=run, daemon=True).start()

    def _after_attach(self, ok: bool) -> None:
        if ok:
            self._set_login_status("已绑定")
            self.confirm_login_btn.configure(state="normal")
        else:
            self._set_login_status("绑定失败")

    def load_cookie_login(self) -> None:
        self._set_login_status("从Cookie恢复中...")

        def run():
            ok = self.session.load_cookies()
            self.after(0, lambda: self._after_cookie(ok))

        threading.Thread(target=run, daemon=True).start()

    def _after_cookie(self, ok: bool) -> None:
        if ok:
            self.is_logged_in = True
            self._set_login_status("已恢复")
            self.start_btn.configure(state="normal")
        else:
            self._set_login_status("恢复失败")

    def confirm_login(self) -> None:
        self.confirm_login_btn.configure(state="disabled")
        self._set_login_status("验证中...")

        def run():
            ok = self.session.confirm_login_and_save_cookies()
            self.after(0, lambda: self._after_confirm_login(ok))

        threading.Thread(target=run, daemon=True).start()

    def _after_confirm_login(self, ok: bool) -> None:
        if ok:
            self.is_logged_in = True
            self._set_login_status("已登录")
            self.start_btn.configure(state="normal")
        else:
            self._set_login_status("未确认（重试）")
            self.confirm_login_btn.configure(state="normal")

    def start_monitoring(self) -> None:
        if not self.is_logged_in:
            self._append_log(f"[{now_ts()}] 请先完成登录")
            return
        if not self.session.driver:
            self._append_log(f"[{now_ts()}] 浏览器不存在，请先打开登录页或绑定")
            return

        refresh_s = self._get_refresh_seconds()
        if refresh_s is None:
            return

        tasks = self._parse_tasks(self.tasks_text.get("1.0", "end").strip())
        if not tasks:
            self._append_log(f"[{now_ts()}] 请至少填写一个任务")
            return

        # Stop previous
        self.stop_event.set()
        self.pause_event.clear()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=0.2)
        self.stop_event.clear()

        self.monitor = DamaiTabMonitor(
            driver=self.session.driver,
            log_queue=self.log_queue,
            event_queue=self.event_queue,
            stop_event=self.stop_event,
            pause_event=self.pause_event,
            refresh_seconds=refresh_s,
        )
        self.monitor.prepare_tabs(tasks)

        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status(f"监控中（{len(tasks)}个任务，{refresh_s:.2f}s刷新）")

        self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True, name="DamaiMonitor")
        self.monitor_thread.start()

    def pause_monitoring(self) -> None:
        self.pause_event.set()
        self.pause_btn.configure(state="disabled")
        self.resume_btn.configure(state="normal")
        self._set_status("已暂停")

    def resume_monitoring(self) -> None:
        self.pause_event.clear()
        self.pause_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")
        self._set_status("监控中")

    def stop_monitoring(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()
        self._set_status("正在停止...")

        def finalize():
            self._set_status("已停止（浏览器保留）")
            if self.is_logged_in:
                self.start_btn.configure(state="normal")
            else:
                self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled")
            self.resume_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            self._append_log(f"[{now_ts()}] 已停止监控（浏览器不会自动关闭）")

        self.after(0, finalize)

    def on_closing(self) -> None:
        try:
            self.stop_monitoring()
        except Exception:
            pass
        self.after(50, self.destroy)

    def _poll_queues(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass

        try:
            while True:
                evt = self.event_queue.get_nowait()
                if evt.get("type") == "purchasable_detected":
                    idx = evt.get("task_index")
                    state_text = evt.get("state_text")
                    url = evt.get("url")
                    msg = f"[{now_ts()}] [提醒] 标签页#{idx} 可能可购买：{state_text} | {url}"
                    self._append_alert(msg)
                    # 连续响铃
                    for _ in range(3):
                        self.bell()
                        time.sleep(0.08)
        except queue.Empty:
            pass

        self.after(60, self._poll_queues)


if __name__ == "__main__":
    app = DamaiUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
