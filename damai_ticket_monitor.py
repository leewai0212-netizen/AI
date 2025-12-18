import os
import time
import pickle
import threading
import queue
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# CustomTkinter 外观
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


@dataclass(frozen=True)
class RefreshIntervals:
    """刷新间隔（毫秒）"""

    initial_ms: int
    normal_ms: int
    late_ms: int

    def clamp(self) -> "RefreshIntervals":
        # 约束范围：过快可能导致页面异常/触发风控/CPU飙升
        initial = max(200, min(self.initial_ms, 5000))
        normal = max(300, min(self.normal_ms, 8000))
        late = max(500, min(self.late_ms, 15000))
        return RefreshIntervals(initial, normal, late)

    @staticmethod
    def ms_to_s(ms: int) -> float:
        return ms / 1000.0


class DamaiTicketMonitor:
    """后端：登录 + 票务状态监控（不自动提交订单）"""

    def __init__(self, log_queue: "queue.Queue[str]", ui_queue: "queue.Queue[dict]"):
        self.log_queue = log_queue
        self.ui_queue = ui_queue

        self.stop_flag = False
        self.is_logged_in = False

        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

        self.cookie_file = "damai_cookies.pkl"

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_queue.put(f"[{ts}] {message}")

    def _ui(self, **payload) -> None:
        """通过队列让主线程更新 UI（避免 Tk 线程问题）"""
        self.ui_queue.put(payload)

    def setup_driver(self) -> bool:
        """启动 Chrome"""
        try:
            self._log("正在启动浏览器...")
            self._ui(status="正在启动浏览器...")

            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # 维持你原来的“指定 Chrome 安装目录”的方式：
            # 注意：binary_location 必须指向 chrome.exe（不能只写文件夹）。
            # 你给的路径是 D:\Chrome\App，因此这里按常见结构拼成 chrome.exe。
            chrome_bin = r"D:\Chrome\App\chrome.exe"
            if os.path.exists(chrome_bin):
                options.binary_location = chrome_bin
            else:
                # 不阻塞：让 Selenium 继续尝试系统默认路径，但会打印提示
                self._log(f"未找到 Chrome 程序: {chrome_bin}（将尝试系统默认安装路径）")

            # 更快进入可交互状态；减少长时间等待
            options.page_load_strategy = "eager"

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            # 建议只使用显式等待，避免隐式/显式混用带来的不可预期延迟
            self.driver.implicitly_wait(0)

            self.driver.set_script_timeout(30)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 10)

            try:
                self.driver.maximize_window()
            except Exception:
                pass

            self.driver.get("about:blank")
            self._log("浏览器启动成功")
            self._ui(status="浏览器已启动")
            return True
        except Exception as e:
            self._log(f"浏览器启动失败: {e}")
            self._ui(status="浏览器启动失败", enable_open_login=True)
            return False

    def open_login_page(self) -> bool:
        """打开登录页"""
        if not self.driver:
            if not self.setup_driver():
                return False

        try:
            self._log("正在打开登录页面...")
            self._ui(status="正在打开登录页...")

            # 先访问首页，提高跳转稳定性
            try:
                self.driver.get("https://www.damai.cn/")
                time.sleep(1.2)
            except Exception:
                pass

            login_url = "https://passport.damai.cn/login?ru=https://www.damai.cn/"
            self.driver.get(login_url)
            time.sleep(1.2)

            self._log(f"当前URL: {self.driver.current_url}")
            self._log("请在浏览器里扫码登录，登录完成后回到本窗口点击：确认登录成功")

            self._ui(status="请扫码登录", enable_confirm=True)
            return True
        except WebDriverException as e:
            self._log(f"打开登录页失败(WebDriver): {e}")
            self._ui(status="打开登录页失败", enable_open_login=True)
            return False
        except Exception as e:
            self._log(f"打开登录页失败: {e}")
            self._ui(status="打开登录页失败", enable_open_login=True)
            return False

    def _save_cookies(self) -> None:
        if not self.driver:
            return
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            self._log("Cookie 已保存")
        except Exception as e:
            self._log(f"Cookie 保存失败: {e}")

    def try_load_cookies(self) -> bool:
        """尝试加载 cookie（不保证有效）"""
        if not self.driver:
            if not self.setup_driver():
                return False

        if not os.path.exists(self.cookie_file):
            self._log("未找到本地 cookie 文件")
            return False

        try:
            self._log("尝试加载本地 Cookie...")
            self.driver.get("https://www.damai.cn/")
            time.sleep(1.0)

            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)

            for c in cookies:
                try:
                    self.driver.add_cookie(c)
                except Exception:
                    continue

            self.driver.get("https://www.damai.cn/")
            time.sleep(1.5)
            self._log("Cookie 已注入，建议点击：确认登录成功")
            self._ui(status="Cookie 已加载（待确认）", enable_confirm=True)
            return True
        except Exception as e:
            self._log(f"加载 Cookie 失败: {e}")
            return False

    def confirm_login(self) -> bool:
        """确认是否已登录"""
        if not self.driver:
            self._log("浏览器未启动")
            return False

        try:
            self._log("正在验证登录状态...")
            self._ui(status="正在验证登录...")

            time.sleep(1.0)
            cur = self.driver.current_url or ""
            if "passport.damai.cn" in cur:
                self._log("仍停留在登录页：请先扫码登录并等待页面跳转")
                self._ui(status="请完成扫码登录", enable_confirm=True)
                return False

            self.driver.get("https://www.damai.cn/")
            time.sleep(2.0)

            page = self.driver.page_source or ""
            if any(k in page for k in ["我的大麦", "个人中心", "退出"]):
                self.is_logged_in = True
                self._save_cookies()
                self._log("登录确认成功")
                self._ui(status="登录成功", enable_start=True)
                return True

            # 兜底：无法强校验时允许继续（由用户自行判断）
            if "passport.damai.cn" not in (self.driver.current_url or ""):
                self.is_logged_in = True
                self._save_cookies()
                self._log("未能强校验登录标识，但已离开登录域名；允许继续")
                self._ui(status="登录可能成功（可继续）", enable_start=True)
                return True

            self._log("无法确认登录状态")
            self._ui(status="登录验证失败", enable_confirm=True)
            return False
        except Exception as e:
            self._log(f"确认登录出错: {e}")
            self._ui(status="登录验证出错", enable_confirm=True)
            return False

    def _safe_click(self, el) -> None:
        """点击兜底：普通 click 失败就用 JS click"""
        try:
            el.click()
        except Exception:
            if not self.driver:
                raise
            self.driver.execute_script("arguments[0].click();", el)

    def monitor_ticket(
        self,
        ticket_url: str,
        session_keyword: str,
        price_keyword: str,
        refresh: RefreshIntervals,
        auto_select: bool = True,
    ) -> bool:
        """持续刷新监控：检测到疑似可购买状态就提醒并返回（不自动下单）"""

        if not self.driver:
            self._log("浏览器未启动")
            return False

        refresh = refresh.clamp()
        self.stop_flag = False

        self._log("监控模式启动（不自动提交订单）")
        self._log(f"刷新间隔(ms): 初始={refresh.initial_ms}, 正常={refresh.normal_ms}, 后期={refresh.late_ms}")
        self._ui(status="监控中...", enable_stop=True)

        attempt = 0
        last_state: Optional[str] = None

        while not self.stop_flag:
            attempt += 1
            try:
                self.driver.get(ticket_url)
                time.sleep(RefreshIntervals.ms_to_s(refresh.initial_ms))

                if auto_select:
                    # 选择场次
                    try:
                        times = self.driver.find_elements(By.CSS_SELECTOR, ".sku-times-list .sku-times-item")
                        if times:
                            chosen = None
                            if session_keyword.strip():
                                for t in times:
                                    if session_keyword.strip() in (t.text or ""):
                                        chosen = t
                                        break
                            chosen = chosen or times[0]
                            self._safe_click(chosen)
                    except Exception:
                        pass

                    time.sleep(RefreshIntervals.ms_to_s(refresh.initial_ms))

                    # 选择价格
                    try:
                        prices = self.driver.find_elements(By.CSS_SELECTOR, ".sku-ticket-list .sku-ticket-item")
                        if prices:
                            chosen = None
                            if price_keyword.strip():
                                for p in prices:
                                    if price_keyword.strip() in (p.text or ""):
                                        chosen = p
                                        break
                            chosen = chosen or prices[0]
                            self._safe_click(chosen)
                    except Exception:
                        pass

                    time.sleep(RefreshIntervals.ms_to_s(refresh.initial_ms))

                # 读取购买按钮状态
                btn_text = None
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, ".buybtn")
                    if btns:
                        btn_text = (btns[0].text or "").strip()
                except Exception:
                    btn_text = None

                state = btn_text or "未找到购买按钮"
                if state != last_state:
                    self._log(f"按钮状态: {state}")
                    last_state = state

                # “疑似可购买”提醒：只提示用户手动下单
                if btn_text and ("缺货" not in btn_text) and any(k in btn_text for k in ["立即", "购买", "选座", "去支付"]):
                    self._log("检测到疑似可购买状态：请立即切到浏览器手动完成下单/支付")
                    self._ui(status="发现可购买（请手动下单）", alert=True, enable_stop=True)
                    return True

                # 动态间隔：严格 ms->s（修复原代码 /10000 的计算错误）
                if attempt < 10:
                    sleep_s = RefreshIntervals.ms_to_s(refresh.initial_ms)
                elif attempt < 60:
                    sleep_s = RefreshIntervals.ms_to_s(refresh.normal_ms)
                else:
                    sleep_s = RefreshIntervals.ms_to_s(refresh.late_ms)

                time.sleep(sleep_s)

            except Exception as e:
                self._log(f"监控出错: {str(e)[:200]}")
                time.sleep(RefreshIntervals.ms_to_s(refresh.normal_ms))

        self._log("已停止监控")
        self._ui(status="已停止", enable_start=True, enable_stop=False)
        return False

    def stop(self) -> None:
        self.stop_flag = True
        self._log("正在停止...")

    def close(self) -> None:
        try:
            if self.driver:
                self.driver.quit()
        finally:
            self.driver = None
            self.wait = None
            self._log("浏览器已关闭")


class DamaiUI(ctk.CTk):
    """前端 UI"""

    def __init__(self):
        super().__init__()

        self.title("大麦网票务监控助手（登录 + 监控提醒）")
        self.geometry("950x820")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.ui_queue: "queue.Queue[dict]" = queue.Queue()

        self.worker: Optional[DamaiTicketMonitor] = None
        self.worker_thread: Optional[threading.Thread] = None

        self._build_widgets()
        self.after(80, self._poll_queues)

    def _ensure_worker(self) -> None:
        if not self.worker:
            self.worker = DamaiTicketMonitor(self.log_queue, self.ui_queue)

    def _build_widgets(self) -> None:
        # 配置区
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(config_frame, text="商品链接:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=6, sticky="w"
        )
        self.ticket_url_entry = ctk.CTkEntry(config_frame, placeholder_text="请输入大麦网商品详情页链接")
        self.ticket_url_entry.grid(row=0, column=1, padx=(5, 10), pady=6, sticky="ew")

        ctk.CTkLabel(config_frame, text="场次关键词:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=10, pady=6, sticky="w"
        )
        self.session_keyword_entry = ctk.CTkEntry(config_frame, placeholder_text="留空则自动选第一个（可选）")
        self.session_keyword_entry.grid(row=1, column=1, padx=(5, 10), pady=6, sticky="ew")

        ctk.CTkLabel(config_frame, text="价格关键词:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, padx=10, pady=6, sticky="w"
        )
        self.price_keyword_entry = ctk.CTkEntry(config_frame, placeholder_text="留空则自动选第一个（可选）")
        self.price_keyword_entry.grid(row=2, column=1, padx=(5, 10), pady=6, sticky="ew")

        # 刷新间隔区
        refresh_frame = ctk.CTkFrame(self)
        refresh_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        for i in range(6):
            refresh_frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(refresh_frame, text="刷新间隔（毫秒）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=6, padx=10, pady=10
        )

        ctk.CTkLabel(refresh_frame, text="初始:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=10, pady=6, sticky="w"
        )
        self.initial_refresh_entry = ctk.CTkEntry(refresh_frame)
        self.initial_refresh_entry.insert(0, "500")
        self.initial_refresh_entry.grid(row=1, column=1, padx=(5, 10), pady=6, sticky="ew")

        ctk.CTkLabel(refresh_frame, text="正常:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=2, padx=10, pady=6, sticky="w"
        )
        self.normal_refresh_entry = ctk.CTkEntry(refresh_frame)
        self.normal_refresh_entry.insert(0, "1200")
        self.normal_refresh_entry.grid(row=1, column=3, padx=(5, 10), pady=6, sticky="ew")

        ctk.CTkLabel(refresh_frame, text="后期:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=4, padx=10, pady=6, sticky="w"
        )
        self.late_refresh_entry = ctk.CTkEntry(refresh_frame)
        self.late_refresh_entry.insert(0, "2000")
        self.late_refresh_entry.grid(row=1, column=5, padx=(5, 10), pady=6, sticky="ew")

        # 控制区
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.open_login_button = ctk.CTkButton(control_frame, text="1. 打开登录页", command=self._open_login)
        self.open_login_button.grid(row=0, column=0, padx=10, pady=10)

        self.load_cookie_button = ctk.CTkButton(control_frame, text="(可选) 载入Cookie", command=self._load_cookie)
        self.load_cookie_button.grid(row=0, column=1, padx=10, pady=10)

        self.confirm_login_button = ctk.CTkButton(
            control_frame, text="2. 确认登录成功", command=self._confirm_login, state="disabled"
        )
        self.confirm_login_button.grid(row=0, column=2, padx=10, pady=10)

        self.start_button = ctk.CTkButton(control_frame, text="3. 开始监控", command=self._start_monitor, state="disabled")
        self.start_button.grid(row=0, column=3, padx=10, pady=10)

        self.stop_button = ctk.CTkButton(
            control_frame,
            text="停止",
            command=self._stop,
            state="disabled",
            width=120,
            fg_color="red",
            hover_color="darkred",
        )
        self.stop_button.grid(row=0, column=4, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(control_frame, text="状态: 未开始", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=0, column=5, padx=20, pady=10, sticky="e")

        # 日志区
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="运行日志", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.log_textbox = ctk.CTkTextbox(log_frame, wrap="word", font=ctk.CTkFont(family="Consolas"))
        self.log_textbox.grid(row=1, column=0, padx=(10, 10), pady=(5, 10), sticky="nsew")

        scrollbar = ctk.CTkScrollbar(log_frame, command=self.log_textbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log_textbox.configure(yscrollcommand=scrollbar.set)

    def _append_log(self, msg: str) -> None:
        self.log_textbox.insert("end", msg + "\n")
        self.log_textbox.see("end")

    def _apply_ui_payload(self, payload: dict) -> None:
        if "status" in payload:
            self.status_label.configure(text=f"状态: {payload['status']}")

        if payload.get("enable_open_login") is True:
            self.open_login_button.configure(state="normal")

        if payload.get("enable_confirm") is True:
            self.confirm_login_button.configure(state="normal")

        if payload.get("enable_start") is True:
            self.start_button.configure(state="normal")

        if payload.get("enable_stop") is True:
            self.stop_button.configure(state="normal")

        if payload.get("enable_stop") is False:
            self.stop_button.configure(state="disabled")

        if payload.get("alert") is True:
            self._append_log("[提醒] 检测到疑似可购买状态，请切到浏览器手动下单")

    def _poll_queues(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass

        try:
            while True:
                payload = self.ui_queue.get_nowait()
                self._apply_ui_payload(payload)
        except queue.Empty:
            pass

        self.after(80, self._poll_queues)

    def _get_refresh(self) -> Optional[RefreshIntervals]:
        try:
            initial = int(self.initial_refresh_entry.get())
            normal = int(self.normal_refresh_entry.get())
            late = int(self.late_refresh_entry.get())
            return RefreshIntervals(initial, normal, late).clamp()
        except ValueError:
            self._append_log("刷新间隔必须是数字")
            return None

    def _open_login(self) -> None:
        self._ensure_worker()
        self.open_login_button.configure(state="disabled")

        def run():
            ok = self.worker.open_login_page() if self.worker else False
            if not ok:
                self.ui_queue.put({"enable_open_login": True})

        threading.Thread(target=run, daemon=True).start()

    def _load_cookie(self) -> None:
        self._ensure_worker()

        def run():
            ok = self.worker.try_load_cookies() if self.worker else False
            if not ok:
                self.log_queue.put("[提示] Cookie 载入失败或不存在，请走扫码登录流程")

        threading.Thread(target=run, daemon=True).start()

    def _confirm_login(self) -> None:
        self._ensure_worker()
        self.confirm_login_button.configure(state="disabled")

        def run():
            ok = self.worker.confirm_login() if self.worker else False
            if not ok:
                self.ui_queue.put({"enable_confirm": True})

        threading.Thread(target=run, daemon=True).start()

    def _start_monitor(self) -> None:
        self._ensure_worker()
        if not self.worker or not self.worker.is_logged_in:
            self._append_log("请先登录")
            return

        url = self.ticket_url_entry.get().strip()
        if not url:
            self._append_log("请输入商品链接")
            return

        refresh = self._get_refresh()
        if not refresh:
            return

        session_kw = self.session_keyword_entry.get().strip()
        price_kw = self.price_keyword_entry.get().strip()

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        def run():
            self.worker.monitor_ticket(
                ticket_url=url,
                session_keyword=session_kw,
                price_keyword=price_kw,
                refresh=refresh,
                auto_select=True,
            )
            self.ui_queue.put({"enable_start": True, "enable_stop": False})

        self.worker_thread = threading.Thread(target=run, daemon=True)
        self.worker_thread.start()

    def _stop(self) -> None:
        if self.worker:
            self.worker.stop()
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="normal")

    def on_closing(self) -> None:
        if self.worker:
            self.worker.stop()
            try:
                if self.worker_thread and self.worker_thread.is_alive():
                    self.worker_thread.join(timeout=2)
            except Exception:
                pass
            self.worker.close()
        self.destroy()


if __name__ == "__main__":
    app = DamaiUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
