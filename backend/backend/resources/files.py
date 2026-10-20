# -*- coding: utf-8 -*-
"""
文件上传模块 —— 契约文档 1.8 节。

接口：
- POST /api/v1/files/upload  上传文件，返回文件 URL

请求类型 multipart/form-data，字段名 file。
仅保存文件到 uploads 目录，返回可访问的 URL 字符串。
"""
import os
import uuid

from flask import request, current_app
from flask_restx import Namespace, Resource

from common.auth import login_required
from common.errors import ApiError, ERR_PARAM
from common.response import success

ns = Namespace("files", description="文件上传")

# 允许的扩展名
ALLOWED = {"png", "jpg", "jpeg", "gif", "pdf", "csv", "xlsx", "doc", "docx"}


@ns.route("/upload")
class Upload(Resource):
    """POST /files/upload —— 上传文件。"""

    @ns.doc("上传文件")
    @login_required
    def post(self):
        """接收 multipart 字段 file，返回 { url }。"""
        if "file" not in request.files:
            raise ApiError(ERR_PARAM, "缺少文件字段 file")
        f = request.files["file"]
        if not f.filename:
            raise ApiError(ERR_PARAM, "文件名为空")

        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED:
            raise ApiError(ERR_PARAM, f"不支持的文件类型：{ext}")

        # 保存到 uploads 目录（相对 backend）
        upload_dir = os.path.join(current_app.root_path, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        saved_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(upload_dir, saved_name))

        # 返回可访问 URL（静态资源由 /uploads 提供）
        url = f"/uploads/{saved_name}"
        return success({"url": url, "filename": saved_name})