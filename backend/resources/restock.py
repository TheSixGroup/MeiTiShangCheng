# -*- coding: utf-8 -*-
"""
补货请求模块 —— 契约文档第 6.2 节。

接口：
- GET  /api/v1/restock-requests               补货申请列表（inventory:view）
- POST /api/v1/restock-requests               提交补货申请（restock:request）
- PUT  /api/v1/restock-requests/{id}/process  处理补货申请（inventory:manage）

处理流程（需求 6.2）：
pending -> processing -> completed（completed 时库存自动增加）

安全要点：
1. 处理接口按契约使用单端点 /process + body { status }。
2. 必须校验状态流转合法性，防止跳过 processing 直接 completed。
3. 库存只在“首次进入 completed”时增加一次，防止重复处理导致库存重复增加。
"""
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource

from common.auth import current_user, current_employee_id, login_required, require_permission
from common.errors import ApiError, ERR_PARAM, ERR_NOT_FOUND, ERR_BUSINESS
from common.response import success, paged

ns = Namespace("restock", description="补货请求")


@ns.route("")
class RestockList(Resource):
    """GET /restock-requests 列表；POST /restock-requests 提交。"""

    @ns.doc("获取补货申请列表")
    @require_permission("inventory:view")
    def get(self):
        """查询参数：page, pageSize, status。"""
        from models import RestockRequest

        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("pageSize", 10)), 1), 100)
        status = request.args.get("status")

        query = RestockRequest.query
        if status:
            query = query.filter_by(status=status)
        total = query.count()
        rows = (query.order_by(RestockRequest.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size).all())
        return paged([r.to_dict() for r in rows], total, page, page_size)

    @ns.doc("提交补货申请")
    @require_permission("restock:request")
    def post(self):
        """请求体：{ productId, requestedQuantity }。"""
        from models import RestockRequest, Product
        from extensions import db

        body = request.get_json(silent=True) or {}
        product_id = body.get("productId")
        qty = body.get("requestedQuantity")
        if not product_id or not qty or int(qty) <= 0:
            raise ApiError(ERR_PARAM, "productId 和正数 requestedQuantity 为必填")

        if not Product.query.get(product_id):
            raise ApiError(ERR_NOT_FOUND, "商品不存在")

        req = RestockRequest(
            product_id=product_id,
            requested_quantity=int(qty),
            requested_by=current_employee_id(),
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        return success(req.to_dict(), "补货申请已提交")


@ns.route("/<string:req_id>/process")
class ProcessRestock(Resource):
    """PUT /restock-requests/{id}/process —— 处理补货申请。"""

    # 合法状态流转：pending -> processing -> completed
    ALLOWED = {
        "pending": {"processing"},
        "processing": {"completed"},
        "completed": set(),
    }

    @ns.doc("处理补货申请")
    @require_permission("inventory:manage")
    def put(self, req_id):
        """请求体：{ status: processing|completed }（契约 6.2）。

        当状态首次变为 completed 时，库存自动增加，
        并记录 processedBy / processedAt。
        """
        from models import RestockRequest, Product
        from extensions import db

        req = RestockRequest.query.get(req_id)
        if not req:
            raise ApiError(ERR_NOT_FOUND, "补货申请不存在")

        body = request.get_json(silent=True) or {}
        target = body.get("status")
        if not target:
            raise ApiError(ERR_PARAM, "缺少参数 status")

        # 校验状态流转合法性
        if target not in self.ALLOWED.get(req.status, set()):
            raise ApiError(
                ERR_BUSINESS,
                f"非法状态流转：{req.status} -> {target}",
            )

        old_status = req.status
        req.status = target
        user = current_user()
        req.processed_by = user.employee_id if user else None
        req.processed_at = datetime.now()

        # 仅在首次完成时增加库存（防止重复处理）
        if target == "completed" and old_status != "completed":
            product = Product.query.get(req.product_id)
            if product:
                product.stock_quantity += req.requested_quantity
                product.last_restocked_at = datetime.now()

        db.session.commit()
        return success(req.to_dict(), "处理成功")