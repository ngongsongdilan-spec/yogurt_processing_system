import json
from django.http import JsonResponse
from django.db import connection, DatabaseError
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render


def landing(request):
    return render(request, 'dashboard/landing.html')

def index(request):
    return render(request, 'dashboard/index.html')


# ================================================================
# AUTH
# ================================================================
@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    try:
        data = json.loads(request.body)
        with connection.cursor() as c:
            c.execute("SELECT u.user_id, u.username, r.role_name, e.employee_name "
                      "FROM user_account u JOIN role r ON u.role_id = r.role_id "
                      "LEFT JOIN employee e ON u.employee_id = e.employee_id "
                      "WHERE u.username = %s AND u.password = %s AND u.is_active = true",
                      [data['username'], data['password']])
            row = c.fetchone()
        if row:
            return JsonResponse({'status': 'success', 'user': {
                'id': row[0], 'username': row[1], 'role': row[2], 'name': row[3]}})
        return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def signup_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    try:
        data = json.loads(request.body)
        with connection.cursor() as c:
            c.execute("SELECT user_id FROM user_account WHERE username = %s", [data['username']])
            if c.fetchone():
                return JsonResponse({'status': 'error', 'message': 'Username already exists'}, status=409)
            c.execute("INSERT INTO user_account (username, password, employee_id, role_id) "
                      "VALUES (%s, %s, NULL, 5) RETURNING user_id",
                      [data['username'], data['password']])
            uid = c.fetchone()[0]
        return JsonResponse({'status': 'success', 'user_id': uid, 'message': 'Account created.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# DASHBOARD
# ================================================================
def dashboard_data(request):
    try:
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM production_batch WHERE status = 'InProgress'")
            active_batches = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM production_batch WHERE status = 'Completed'")
            completed_batches = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(quantity_on_hand), 0) FROM inventory")
            raw_stock = float(c.fetchone()[0])
            c.execute("SELECT COALESCE(SUM(quantity_on_hand), 0) FROM product_inventory")
            prod_stock = float(c.fetchone()[0])
            c.execute("SELECT COUNT(*) FROM quality_control WHERE status = 'Fail'")
            qc_fails = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM machine WHERE status = 'Operational'")
            machines_op = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM sales_order WHERE status = 'Pending'")
            pending_orders = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM audit_log WHERE changed_at >= now() - interval '24 hours'")
            recent_audits = c.fetchone()[0]
        return JsonResponse({'status': 'success', 'data': {
            'active_batches': active_batches,
            'completed_batches': completed_batches,
            'raw_stock': raw_stock,
            'prod_stock': prod_stock,
            'qc_fails': qc_fails,
            'machines_operational': machines_op,
            'pending_orders': pending_orders,
            'recent_audits': recent_audits,
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# INVENTORY
# ================================================================
def inventory_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT rm.material_name, i.quantity_on_hand, i.reserved_qty,
                       u.uom_code, l.batch_no, l.expiry_date
                FROM inventory i
                JOIN raw_material rm ON i.material_id = rm.material_id
                JOIN unit_of_measure u ON i.uom_id = u.uom_id
                JOIN lot l ON i.lot_id = l.lot_id
                ORDER BY rm.material_name
            """)
            raw = [dict(zip(['material', 'qty', 'reserved', 'uom', 'lot', 'expiry'], r)) for r in c.fetchall()]
            c.execute("""
                SELECT p.product_name, pi.quantity_on_hand, pi.reserved_qty,
                       u.uom_code, pb.batch_id, pi.expiry_date
                FROM product_inventory pi
                JOIN product p ON pi.product_id = p.product_id
                JOIN unit_of_measure u ON pi.uom_id = u.uom_id
                LEFT JOIN production_batch pb ON pi.batch_id = pb.batch_id
                ORDER BY p.product_name
            """)
            prod = [dict(zip(['product', 'qty', 'reserved', 'uom', 'batch', 'expiry'], r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'raw_materials': raw, 'finished_goods': prod})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# PRODUCTION BATCHES
# ================================================================
def batches_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT pb.batch_id, p.product_name, pb.batch_date, pb.planned_qty,
                       pb.actual_qty, pb.status, e.employee_name, r.recipe_name
                FROM production_batch pb
                JOIN product p ON pb.product_id = p.product_id
                LEFT JOIN employee e ON pb.created_by = e.employee_id
                LEFT JOIN recipe r ON pb.recipe_id = r.recipe_id
                ORDER BY pb.batch_date DESC
            """)
            cols = ['id', 'product', 'date', 'planned', 'actual', 'status', 'created_by', 'recipe']
            batches = [dict(zip(cols, r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'batches': batches})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# QUALITY CONTROL
# ================================================================
@csrf_exempt
def quality_control_view(request):
    if request.method == 'GET':
        try:
            with connection.cursor() as c:
                c.execute("""
                    SELECT qc.qcid, qc.batch_id, qc.inspection_date, qc.status,
                           qc.remarks, e.employee_name, pb.status AS batch_status
                    FROM quality_control qc
                    LEFT JOIN employee e ON qc.inspector_id = e.employee_id
                    LEFT JOIN production_batch pb ON qc.batch_id = pb.batch_id
                    ORDER BY qc.inspection_date DESC
                """)
                cols = ['id', 'batch', 'date', 'status', 'remarks', 'inspector', 'batch_status']
                records = [dict(zip(cols, r)) for r in c.fetchall()]
            return JsonResponse({'status': 'success', 'records': records})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute("SELECT employee_id FROM employee WHERE employee_name = %s",
                          [data.get('inspector', '')])
                emp = c.fetchone()
                if not emp:
                    return JsonResponse({'status': 'error', 'message': 'Inspector not found'}, status=400)
                c.execute(
                    "INSERT INTO quality_control (batch_id, inspector_id, status, remarks) "
                    "VALUES (%s, %s, %s, %s)",
                    [data['batch_id'], emp[0], data['status'], data.get('remarks', '')]
                )
            return JsonResponse({'status': 'success', 'message': 'QC result recorded.'})
        except DatabaseError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# MACHINES
# ================================================================
def machines_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT m.machine_id, m.machine_name, m.machine_type, m.location,
                       m.status, m.purchase_date,
                       (SELECT COUNT(*) FROM maintenance mt WHERE mt.machine_id = m.machine_id) AS maint_count,
                       (SELECT MAX(mt.next_due_date) FROM maintenance mt WHERE mt.machine_id = m.machine_id) AS next_maint
                FROM machine m ORDER BY m.machine_name
            """)
            cols = ['id', 'name', 'type', 'location', 'status', 'purchased', 'maint_count', 'next_maint']
            machines = [dict(zip(cols, r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'machines': machines})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# AUDIT TRAIL
# ================================================================
def audit_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT audit_id, table_name, operation, record_id, changed_by,
                       changed_at, old_data, new_data
                FROM audit_log
                ORDER BY changed_at DESC LIMIT 100
            """)
            cols = ['id', 'table', 'operation', 'record_id', 'changed_by', 'changed_at', 'old_data', 'new_data']
            entries = []
            for r in c.fetchall():
                entry = dict(zip(cols, r))
                if entry['old_data']:
                    entry['old_data'] = json.dumps(entry['old_data'], default=str)
                if entry['new_data']:
                    entry['new_data'] = json.dumps(entry['new_data'], default=str)
                entries.append(entry)
        return JsonResponse({'status': 'success', 'entries': entries})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# PURCHASING
# ================================================================
def purchasing_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT po.poid, s.supplier_name, po.order_date, po.status, po.total_amount,
                       (SELECT COUNT(*) FROM purchase_order_line pol WHERE pol.poid = po.poid) AS line_count
                FROM purchase_order po
                JOIN supplier s ON po.supplier_id = s.supplier_id
                ORDER BY po.order_date DESC
            """)
            cols = ['id', 'supplier', 'date', 'status', 'total', 'lines']
            orders = [dict(zip(cols, r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'orders': orders})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# SALES
# ================================================================
def sales_data(request):
    try:
        with connection.cursor() as c:
            c.execute("""
                SELECT so.sales_id, c.customer_name, so.sale_date, so.status,
                       so.total_amount,
                       (SELECT COUNT(*) FROM sales_order_line sol WHERE sol.sales_id = so.sales_id) AS line_count
                FROM sales_order so
                JOIN customer c ON so.customer_id = c.customer_id
                ORDER BY so.sale_date DESC
            """)
            cols = ['id', 'customer', 'date', 'status', 'total', 'lines']
            orders = [dict(zip(cols, r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'orders': orders})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# SECURITY TRIGGER TEST
# ================================================================
@csrf_exempt
def trigger_test_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    try:
        data = json.loads(request.body)
        test_type = data.get('test', 'completed_batch')
        with connection.cursor() as c:
            if test_type == 'completed_batch':
                c.execute("UPDATE production_batch SET status = 'Tampered' WHERE batch_id = %s",
                          [data.get('batch_id', 1)])
                return JsonResponse({'status': 'success', 'message': 'Unexpected: update succeeded!'})
            elif test_type == 'qc_approved':
                c.execute("UPDATE quality_control SET status = 'Fail' WHERE qcid = %s",
                          [data.get('qcid', 1)])
                return JsonResponse({'status': 'success', 'message': 'Unexpected: QC edit succeeded!'})
            elif test_type == 'check_constraint':
                c.execute("INSERT INTO production_batch (product_id, recipe_id, planned_qty, status, created_by) "
                          "VALUES (1, 1, -100, 'Planned', 1)")
                return JsonResponse({'status': 'success', 'message': 'Unexpected: negative qty allowed!'})
            elif test_type == 'unique_violation':
                c.execute("INSERT INTO user_account (username, password) VALUES (%s, 'test')",
                          [data.get('username', 'admin')])
                return JsonResponse({'status': 'success', 'message': 'Unexpected: duplicate allowed!'})
    except DatabaseError as e:
        error_msg = str(e)
        return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# EXPLORER: raw SQL query tool for testing
# ================================================================
@csrf_exempt
def sql_explorer(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        if not query:
            return JsonResponse({'status': 'error', 'message': 'Query is empty'}, status=400)
        lower = query.lower()
        if any(kw in lower for kw in ['drop', 'truncate', 'delete', 'alter', 'create']):
            return JsonResponse({'status': 'error', 'message': 'Only SELECT/INSERT/UPDATE allowed in explorer'}, status=403)
        with connection.cursor() as c:
            c.execute(query)
            if lower.startswith('select'):
                cols = [desc[0] for desc in c.description]
                rows = [list(r) for r in c.fetchall()]
                return JsonResponse({'status': 'success', 'columns': cols, 'rows': rows, 'count': len(rows)})
            else:
                return JsonResponse({'status': 'success', 'message': 'Query executed successfully.'})
    except DatabaseError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
