import os
import time
import pickle
import threading
import queue
import customtkinter as ctk
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

# Selenium 相关导入
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager


# 设置 CustomTkinter 的外观
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# 全局常量配置
MIN_REFRESH_INTERVAL = {"initial": 50, "normal": 100, "late": 200}
MAX_REFRESH_INTERVAL = {"initial": 1000, "normal": 2000, "late": 3000}
COOKIE_FILE = "damai_cookies.pkl"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 文案/关键词（仅用于“提醒”，不自动点击）
PURCHASABLE_KEYWORDS = ["立即", "购票", "购买", "选座", "去支付"]
NOT_PURCHASABLE_KEYWORDS = ["缺货", "无票", "登记", "缺货登记", "提交缺货登记"]
MOBILE_POPUP_KEYWORDS = ["移步手机端", "手机端购买", "不，立即购票", "不，立即预订", "不，选座购票"]


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


@dataclass
class MonitorTask:
    url: str
    session_keyword: str = ""
    price_keyword: str = ""
    handle: Optional[str] = None
    last_button_text: Optional[str] = None


class DamaiLoginSession:
    """登录会话：打开登录页 -> 扫码 -> 确认登录 -> 保存 Cookie

    关键点：
    - 登录浏览器会一直保持打开，后续监控直接复用这个浏览器（不再二次打开/重复登录）。
    """

    def __init__(
        self,
        log_queue: "queue.Queue[str]",
        chrome_binary_candidates: List[str],
        cookie_file: str = COOKIE_FILE,
    ):
        self.log_queue = log_queue
        self.chrome_binary_candidates = chrome_binary_candidates
        self.cookie_file = cookie_file

        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _log(self, msg: str) -> None:
        self.log_queue.put(f"[{now_ts()}] [登录] {msg}")

    def setup_driver(self) -> bool:
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")
            options.add_argument("--disable-gpu")
            options.add_argument("--start-maximized")
            options.page_load_strategy = "eager"

            for p in self.chrome_binary_candidates:
                if os.path.exists(p):
                    options.binary_location = p
                    self._log(f"使用Chrome路径：{p}")
                    break

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_script_timeout(15)
            self.driver.set_page_load_timeout(20)
            self.driver.implicitly_wait(1)
            self.wait = WebDriverWait(self.driver, 8, poll_frequency=0.25)
            return True
        except Exception as e:
            self._log(f"启动浏览器失败：{str(e)[:160]}")
            return False

    def open_login_page(self) -> bool:
        if not self.driver:
            if not self.setup_driver():
                return False

        try:
            self._log("正在打开登录页面...")
            try:
                self.driver.get("https://www.damai.cn/")
                time.sleep(1.0)
            except Exception:
                pass

            login_url = "https://passport.damai.cn/login?ru=https://www.damai.cn/"
            self.driver.get(login_url)
            time.sleep(1.5)
            self._log(f"当前URL：{self.driver.current_url}")
            self._log("请在浏览器中扫码登录，完成后点击 UI 的“2. 确认登录成功”")
            return True
        except Exception as e:
            self._log(f"打开登录页失败：{str(e)[:160]}")
            return False

    def _save_cookies(self) -> bool:
        if not self.driver:
            return False
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            self._log(f"Cookie 已保存：{self.cookie_file}")
            return True
        except Exception as e:
            self._log(f"Cookie 保存失败：{str(e)[:160]}")
            return False

    def confirm_login(self) -> bool:
        if not self.driver:
            self._log("浏览器未启动")
            return False

        try:
            self._log("正在验证登录状态...")

            # 回首页做检测
            self.driver.get("https://www.damai.cn/")
            time.sleep(2.0)

            page = (self.driver.page_source or "")
            if any(k in page for k in ["我的大麦", "个人中心", "退出"]):
                self._log("检测到登录标识：登录成功")
                self._save_cookies()
                return True

            # 兜底：如果已经不在 passport 域，也认为可继续
            if "passport.damai.cn" not in (self.driver.current_url or ""):
                self._log("未强校验到标识，但已离开登录域名：允许继续")
                self._save_cookies()
                return True

            self._log("未能确认登录，请再试一次")
            return False
        except Exception as e:
            self._log(f"确认登录出错：{str(e)[:160]}")
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
    """复用“已登录浏览器”的多标签页轮询监控（单线程更稳定）"""

    def __init__(
        self,
        driver: webdriver.Chrome,
        log_queue: "queue.Queue[str]",
        event_queue: "queue.Queue[dict]",
        stop_event: threading.Event,
        refresh_intervals: Dict[str, int],
    ):
        self.driver = driver
        self.log_queue = log_queue
        self.event_queue = event_queue
        self.stop_event = stop_event
        self.refresh_intervals = refresh_intervals

        self.tasks: List[MonitorTask] = []

    def _log(self, msg: str) -> None:
        self.log_queue.put(f"[{now_ts()}] [监控] {msg}")

    def _emit(self, **payload) -> None:
        self.event_queue.put(payload)

    def _scan_mobile_popup_text(self) -> Optional[str]:
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            txt = (body.text or "").strip()
            for k in MOBILE_POPUP_KEYWORDS:
                if k in txt:
                    return k
        except Exception:
            return None
        return None

    def _get_buy_button_text(self) -> Optional[str]:
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, ".buybtn")
            if not btns:
                return None
            return (btns[0].text or "").strip()
        except Exception:
            return None

    def _try_select(self, selector: str, keyword: str) -> None:
        if not keyword:
            return
        try:
            els = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if not els:
                return
            for el in els:
                txt = (el.text or "").strip()
                if keyword in txt:
                    try:
                        self.driver.execute_script("arguments[0].click();", el)
                    except Exception:
                        try:
                            el.click()
                        except Exception:
                            return
                    return
        except StaleElementReferenceException:
            return
        except Exception:
            return

    def prepare_tabs(self, tasks: List[MonitorTask]) -> None:
        """为每个任务开一个 tab 并记录 handle（复用同一个浏览器窗口）"""
        self.tasks = []

        base_handle = self.driver.current_window_handle

        # 先确保在 damai 域（减少新 tab 某些域 cookie 行为差异）
        try:
            self.driver.get("https://www.damai.cn/")
            time.sleep(0.8)
        except Exception:
            pass

        for idx, t in enumerate(tasks, start=1):
            url = t.url.strip()
            if not url:
                continue

            # 开新 tab
            self.driver.switch_to.window(base_handle)
            self.driver.execute_script("window.open('about:blank','_blank');")
            handles = self.driver.window_handles
            new_handle = handles[-1]

            self.driver.switch_to.window(new_handle)
            try:
                self.driver.get(url)
            except Exception:
                pass

            self._log(f"已打开标签页#{idx}: {url}")
            self.tasks.append(
                MonitorTask(
                    url=url,
                    session_keyword=t.session_keyword,
                    price_keyword=t.price_keyword,
                    handle=new_handle,
                    last_button_text=None,
                )
            )

        # 回到主 tab
        try:
            self.driver.switch_to.window(base_handle)
        except Exception:
            pass

    def run(self) -> None:
        attempt = 0
        settle_ms = max(20, min(self.refresh_intervals["initial"], 120))

        self._log(f"开始轮询监控：任务数={len(self.tasks)}（同一浏览器多标签页，不重复登录）")

        while not self.stop_event.is_set():
            attempt += 1

            # 动态间隔（严格按毫秒）
            if attempt < 10:
                sleep_ms = self.refresh_intervals["initial"]
            elif attempt < 60:
                sleep_ms = self.refresh_intervals["normal"]
            else:
                sleep_ms = self.refresh_intervals["late"]

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
                    # 刷新当前 tab
                    try:
                        self.driver.refresh()
                    except Exception:
                        try:
                            self.driver.get(task.url)
                        except Exception:
                            pass

                    time.sleep(settle_ms / 1000.0)

                    # 预选场次/票档（仅预选，不做任何购票点击）
                    self._try_select(".sku-times-list .sku-times-item", task.session_keyword)
                    time.sleep(settle_ms / 1000.0)
                    self._try_select(".sku-ticket-list .sku-ticket-item", task.price_keyword)
                    time.sleep(settle_ms / 1000.0)

                    popup_hit = self._scan_mobile_popup_text()
                    if popup_hit:
                        self._emit(type="popup_detected", task_index=idx, text=popup_hit, url=task.url)

                    btn_text = self._get_buy_button_text()
                    if btn_text and btn_text != task.last_button_text:
                        self._log(f"标签页#{idx} 按钮状态：{btn_text}")
                        task.last_button_text = btn_text

                    if btn_text:
                        if any(k in btn_text for k in NOT_PURCHASABLE_KEYWORDS):
                            pass
                        elif any(k in btn_text for k in PURCHASABLE_KEYWORDS):
                            self._emit(
                                type="purchasable_detected",
                                task_index=idx,
                                button_text=btn_text,
                                url=task.url,
                                session_keyword=task.session_keyword,
                                price_keyword=task.price_keyword,
                            )

                except TimeoutException:
                    self._log(f"标签页#{idx} 页面加载超时")
                except WebDriverException as e:
                    self._log(f"标签页#{idx} WebDriver异常：{str(e)[:120]}")
                except Exception as e:
                    self._log(f"标签页#{idx} 异常：{str(e)[:120]}")

                # tab 之间小停顿，避免疯狂切换卡 UI
                time.sleep(0.02)

            # 一轮结束后按间隔等待
            time.sleep(sleep_ms / 1000.0)

        self._log("监控已停止（浏览器保持打开，不会强制退出）")


class DamaiUI(ctk.CTk):
    """多任务监控提醒版 UI（包含：打开登录页/确认登录；监控复用同一浏览器，不重复登录）"""

    def __init__(self):
        super().__init__()

        self.title("大麦网监控提醒版（含登录，复用浏览器，不自动点击/不自动下单）")
        self.geometry("1100x930")
        self.minsize(900, 720)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.event_queue: "queue.Queue[dict]" = queue.Queue()

        self.stop_event = threading.Event()

        self.chrome_binary_candidates = [
            r"D:\Chrome\App\chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        self.login = DamaiLoginSession(self.log_queue, self.chrome_binary_candidates)
        self.is_logged_in = False

        self.monitor: Optional[DamaiTabMonitor] = None
        self.monitor_thread: Optional[threading.Thread] = None

        self._build_widgets()
        self.after(80, self._poll_queues)

    def _build_widgets(self) -> None:
        # ---- 登录区 ----
        login_frame = ctk.CTkFrame(self)
        login_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        login_frame.grid_columnconfigure(4, weight=1)

        self.open_login_btn = ctk.CTkButton(login_frame, text="1. 打开登录页", command=self.open_login_page)
        self.open_login_btn.grid(row=0, column=0, padx=10, pady=10)

        self.confirm_login_btn = ctk.CTkButton(
            login_frame, text="2. 确认登录成功", command=self.confirm_login, state="disabled"
        )
        self.confirm_login_btn.grid(row=0, column=1, padx=10, pady=10)

        self.login_status = ctk.CTkLabel(login_frame, text="登录状态: 未登录", font=ctk.CTkFont(weight="bold"))
        self.login_status.grid(row=0, column=4, padx=10, pady=10, sticky="e")

        # ---- 配置区：多行任务输入 ----
        config = ctk.CTkFrame(self)
        config.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        config.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            config,
            text="监控任务（每行一个）格式：链接 | 场次关键词(可空) | 价格关键词(可空)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")

        self.tasks_text = ctk.CTkTextbox(
            config, height=120, wrap="word", font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.tasks_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.tasks_text.insert("end", "https://www.damai.cn/  |  | \n")

        # ---- 刷新间隔 ----
        refresh = ctk.CTkFrame(self)
        refresh.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        for i in range(6):
            refresh.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(refresh, text="刷新间隔（毫秒）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=6, padx=10, pady=10, sticky="w"
        )

        ctk.CTkLabel(refresh, text="初始:").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self.initial_entry = ctk.CTkEntry(refresh)
        self.initial_entry.insert(0, "100")
        self.initial_entry.grid(row=1, column=1, padx=(0, 10), pady=6, sticky="ew")

        ctk.CTkLabel(refresh, text="正常:").grid(row=1, column=2, padx=10, pady=6, sticky="w")
        self.normal_entry = ctk.CTkEntry(refresh)
        self.normal_entry.insert(0, "200")
        self.normal_entry.grid(row=1, column=3, padx=(0, 10), pady=6, sticky="ew")

        ctk.CTkLabel(refresh, text="后期:").grid(row=1, column=4, padx=10, pady=6, sticky="w")
        self.late_entry = ctk.CTkEntry(refresh)
        self.late_entry.insert(0, "500")
        self.late_entry.grid(row=1, column=5, padx=(0, 10), pady=6, sticky="ew")

        # ---- 控制区 ----
        control = ctk.CTkFrame(self)
        control.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        control.grid_columnconfigure(3, weight=1)

        self.start_btn = ctk.CTkButton(control, text="开始监控（复用浏览器）", command=self.start_monitoring, state="disabled")
        self.start_btn.grid(row=0, column=0, padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(
            control,
            text="停止",
            command=self.stop_monitoring,
            state="disabled",
            fg_color="red",
            hover_color="darkred",
        )
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(control, text="状态: 未开始", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=0, column=3, padx=10, pady=10, sticky="e")

        # ---- 提醒区 ----
        alert = ctk.CTkFrame(self)
        alert.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        alert.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(alert, text="提醒面板（发现可购买/弹窗文本会在这里提示）", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 6), sticky="w"
        )
        self.alert_text = ctk.CTkTextbox(
            alert, height=100, wrap="word", font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.alert_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # ---- 日志区 ----
        logf = ctk.CTkFrame(self)
        logf.grid(row=5, column=0, padx=10, pady=(5, 10), sticky="nsew")
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

    def _get_refresh(self) -> Optional[Dict[str, int]]:
        try:
            initial = int(self.initial_entry.get())
            normal = int(self.normal_entry.get())
            late = int(self.late_entry.get())

            initial = max(MIN_REFRESH_INTERVAL["initial"], min(initial, MAX_REFRESH_INTERVAL["initial"]))
            normal = max(MIN_REFRESH_INTERVAL["normal"], min(normal, MAX_REFRESH_INTERVAL["normal"]))
            late = max(MIN_REFRESH_INTERVAL["late"], min(late, MAX_REFRESH_INTERVAL["late"]))

            return {"initial": initial, "normal": normal, "late": late}
        except ValueError:
            self._append_log(f"[{now_ts()}] 刷新间隔必须是整数")
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

    # ---------- 登录按钮动作 ----------
    def open_login_page(self) -> None:
        self.open_login_btn.configure(state="disabled")
        self.confirm_login_btn.configure(state="disabled")
        self._set_login_status("打开登录页中...")

        def run():
            ok = self.login.open_login_page()
            self.after(0, lambda: self._after_open_login(ok))

        threading.Thread(target=run, daemon=True).start()

    def _after_open_login(self, ok: bool) -> None:
        if ok:
            self._set_login_status("请扫码登录")
            self.confirm_login_btn.configure(state="normal")
        else:
            self._set_login_status("打开失败")
            self.open_login_btn.configure(state="normal")

    def confirm_login(self) -> None:
        self.confirm_login_btn.configure(state="disabled")
        self._set_login_status("验证中...")

        def run():
            ok = self.login.confirm_login()
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

    # ---------- 监控按钮动作 ----------
    def start_monitoring(self) -> None:
        if not self.is_logged_in:
            self._append_log(f"[{now_ts()}] 请先完成登录")
            return
        if not self.login.driver:
            self._append_log(f"[{now_ts()}] 登录浏览器不存在，请先打开登录页")
            return

        refresh = self._get_refresh()
        if not refresh:
            return

        tasks = self._parse_tasks(self.tasks_text.get("1.0", "end").strip())
        if not tasks:
            self._append_log(f"[{now_ts()}] 请至少填写一个任务行")
            return

        # 停止旧监控
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout=0.5)
            except Exception:
                pass
        self.stop_event.clear()

        self.monitor = DamaiTabMonitor(
            driver=self.login.driver,
            log_queue=self.log_queue,
            event_queue=self.event_queue,
            stop_event=self.stop_event,
            refresh_intervals=refresh,
        )
        self.monitor.prepare_tabs(tasks)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status(f"监控中（任务数: {len(tasks)}）")

        self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        self.stop_event.set()
        self._set_status("正在停止...")

        def finalize():
            self._set_status("已停止（浏览器保留）")
            if self.is_logged_in:
                self.start_btn.configure(state="normal")
            else:
                self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            self._append_log(f"[{now_ts()}] 已停止（浏览器不会自动关闭，避免重复登录）")

        self.after(100, finalize)

    def on_closing(self) -> None:
        try:
            self.stop_monitoring()
        except Exception:
            pass
        # 关闭窗口时不强制关闭浏览器（避免你担心的重复登录）；如需关闭可自行关 Chrome
        self.after(150, self.destroy)

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
                et = evt.get("type")
                if et == "purchasable_detected":
                    msg = (
                        f"[{now_ts()}] [提醒] [标签页#{evt.get('task_index')}] 发现疑似可购买：{evt.get('button_text')} | "
                        f"{evt.get('url')} | 场次:{evt.get('session_keyword')} | 价格:{evt.get('price_keyword')}"
                    )
                    self._append_alert(msg)
                    self.bell()
                elif et == "popup_detected":
                    msg = (
                        f"[{now_ts()}] [提醒] [标签页#{evt.get('task_index')}] 检测到弹窗/提示文本：{evt.get('text')} | "
                        f"{evt.get('url')}"
                    )
                    self._append_alert(msg)
                    self.bell()
        except queue.Empty:
            pass

        self.after(80, self._poll_queues)


if __name__ == "__main__":
    app = DamaiUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
