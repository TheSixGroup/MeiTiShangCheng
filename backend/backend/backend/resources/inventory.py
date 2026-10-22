# -*- coding: utf-8 -*-
"""
库存管理模块 —— 契约文档第 6.1 节。

接口：
- GET /api/v1/inventory            库存列表（inventory:view）
- GET /api/v1/inventory/low-stock  低库存预警（inventory:view）

库存只增不减（需求 6 节简化处理），不涉及销售扣减。
"""
from flask import request
from flask_restx import Namespace, Resource

from common.auth import require_permission
from common.response import success, paged

ns = Namespace("inventory", description="库存管理")


@ns.route("")
class InventoryList(Resource):
    """GET /inventory —— 库存列表（分页）。"""

    @ns.doc("获取库存列表")
    @require_permission("inventory:view")
    def get(self):
        """查询参数：page, pageSize, keyword, categoryId, status。"""
        from models import Product

        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("pageSize", 10)), 1), 100)
        keyword = (request.args.get("keyword") or "").strip()
        category_id = request.args.get("categoryId")
        status = request.args.get("status")

        query = Product.query
        if keyword:
            like = f"%{keyword}%"
            from sqlalchemy import or_
            query = query.filter(or_(Product.name.like(like), Product.sku.like(like)))
        if category_id:
            query = query.filter(Product.category_id == category_id)

        # status 为计算字段，需在 Python 层过滤
        all_rows = query.order_by(Product.name).all()
        if status:
            all_rows = [p for p in all_rows if p.calc_status() == status]

        total = len(all_rows)
        start = (page - 1) * page_size
        rows = all_rows[start:start + page_size]
        return paged([p.to_dict() for p in rows], total, page, page_size)


@ns.route("/low-stock")
class LowStock(Resource):
    """GET /inventory/low-stock —— 低库存预警列表。"""

    @ns.doc("获取低库存预警列表")
    @require_permission("inventory:view")
    def get(self):
        """返回低于最低库存线（含缺货）的商品列表。"""
        from models import Product

        rows = Product.query.all()
        low = [p for p in rows if p.calc_status() in ("low_stock", "out_of_stock")]
        return success([p.to_dict() for p in low])