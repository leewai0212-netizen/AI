"""
OSS Hot Update Helper
======================

This utility provides a small desktop GUI for uploading files to Aliyun OSS
and exposes a lightweight HTTP API that clients (e.g. 按键精灵安卓脚本) can call
to determine whether a new version is available.

Dependencies:
    pip install pyqt5 fastapi uvicorn oss2

Usage:
    python oss_updater.py

Within the GUI fill in your OSS credentials, select the file you want to publish,
provide a version string (e.g. 1.0.3) and click “上传并发布”.
Once at least one release is published, click “启动本地API” to start an HTTP server
that exposes /status and /download endpoints for the Android client.
"""

import json
import threading
from pathlib import Path
from typing import Optional

import oss2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from PyQt5 import QtCore, QtGui, QtWidgets

META_FILE = Path("release_meta.json")
DEFAULT_PORT = 6655


def load_metadata() -> Optional[dict]:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def save_metadata(data: dict) -> None:
    META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class OSSUploader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("阿里云OSS 热更新工具")
        self.setMinimumSize(620, 420)
        self.api_thread: Optional[threading.Thread] = None
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()

        self.ak_input = QtWidgets.QLineEdit()
        self.ak_input.setPlaceholderText("AccessKey ID")
        form.addRow("AccessKey ID", self.ak_input)

        self.secret_input = QtWidgets.QLineEdit()
        self.secret_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.secret_input.setPlaceholderText("AccessKey Secret")
        form.addRow("AccessKey Secret", self.secret_input)

        self.endpoint_input = QtWidgets.QLineEdit()
        self.endpoint_input.setPlaceholderText("例如：https://oss-cn-hangzhou.aliyuncs.com")
        form.addRow("Endpoint", self.endpoint_input)

        self.bucket_input = QtWidgets.QLineEdit()
        self.bucket_input.setPlaceholderText("Bucket 名称")
        form.addRow("Bucket", self.bucket_input)

        object_layout = QtWidgets.QHBoxLayout()
        self.object_input = QtWidgets.QLineEdit()
        self.object_input.setPlaceholderText("远端对象名, 例如: releases/app.apk")
        object_layout.addWidget(self.object_input)
        self.file_button = QtWidgets.QPushButton("选择文件")
        self.file_button.clicked.connect(self.choose_file)
        object_layout.addWidget(self.file_button)
        form.addRow("上传文件", object_layout)

        self.version_input = QtWidgets.QLineEdit()
        self.version_input.setPlaceholderText("例如 1.0.3 或 2025-02-01")
        form.addRow("版本号", self.version_input)

        self.desc_input = QtWidgets.QLineEdit()
        self.desc_input.setPlaceholderText("更新说明，可选")
        form.addRow("描述", self.desc_input)

        layout.addLayout(form)

        self.status_box = QtWidgets.QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setMinimumHeight(150)
        layout.addWidget(self.status_box)

        button_layout = QtWidgets.QHBoxLayout()
        self.upload_button = QtWidgets.QPushButton("上传并发布")
        self.upload_button.clicked.connect(self.upload_release)
        button_layout.addWidget(self.upload_button)

        self.api_button = QtWidgets.QPushButton("启动本地API")
        self.api_button.clicked.connect(self.start_api_server)
        button_layout.addWidget(self.api_button)
        layout.addLayout(button_layout)

    def log(self, message: str):
        self.status_box.append(message)
        self.status_box.moveCursor(QtGui.QTextCursor.End)

    def choose_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择要上传的文件")
        if file_path:
            self.object_input.setText(self.object_input.text() or Path(file_path).name)
            self.object_input.setProperty("local_file", file_path)
            self.log(f"已选择文件: {file_path}")

    def upload_release(self):
        local_file = self.object_input.property("local_file")
        if not local_file:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择需要上传的文件。")
            return
        required = [
            (self.ak_input.text().strip(), "AccessKey ID"),
            (self.secret_input.text().strip(), "AccessKey Secret"),
            (self.endpoint_input.text().strip(), "Endpoint"),
            (self.bucket_input.text().strip(), "Bucket"),
            (self.object_input.text().strip(), "远端对象名"),
            (self.version_input.text().strip(), "版本号"),
        ]
        for value, label in required:
            if not value:
                QtWidgets.QMessageBox.warning(self, "提示", f"{label} 不能为空")
                return

        try:
            auth = oss2.Auth(self.ak_input.text().strip(), self.secret_input.text().strip())
            bucket = oss2.Bucket(auth, self.endpoint_input.text().strip(), self.bucket_input.text().strip())
            with open(local_file, "rb") as file_stream:
                result = bucket.put_object(self.object_input.text().strip(), file_stream)
            object_url = f"https://{self.bucket_input.text().strip()}.{self.endpoint_input.text().strip().replace('https://', '').replace('http://', '')}/{self.object_input.text().strip()}"
            metadata = {
                "version": self.version_input.text().strip(),
                "description": self.desc_input.text().strip(),
                "object": self.object_input.text().strip(),
                "etag": getattr(result, "etag", ""),
                "url": object_url,
                "uploaded_at": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate),
            }
            save_metadata(metadata)
            self.log(f"上传成功：{metadata['object']} -> {metadata['url']}")
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QMessageBox.critical(self, "上传失败", str(exc))
            self.log(f"上传失败: {exc}")

    def start_api_server(self):
        if self.api_thread and self.api_thread.is_alive():
            QtWidgets.QMessageBox.information(self, "提示", f"API 已在 {DEFAULT_PORT} 端口运行")
            return

        def run_server():
            app = FastAPI()
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            @app.get("/status")
            def check_status(version: str = Query("", description="客户端当前版本")):
                meta = load_metadata()
                if not meta:
                    raise HTTPException(404, detail="暂无发布记录")
                need_update = (version.strip() != meta.get("version"))
                return {"need_update": need_update, "meta": meta}

            @app.get("/download")
            def download():
                meta = load_metadata()
                if not meta:
                    raise HTTPException(404, detail="暂无发布记录")
                return meta

            self.log(f"API 监听端口: {DEFAULT_PORT}")
            uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT, log_level="info")

        self.api_thread = threading.Thread(target=run_server, daemon=True)
        self.api_thread.start()
        QtWidgets.QMessageBox.information(self, "提示", f"API 已启动: http://127.0.0.1:{DEFAULT_PORT}/status")


def main():
    app = QtWidgets.QApplication([])
    window = OSSUploader()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
