import json
from django.http import JsonResponse
from django.db import connection, DatabaseError
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password


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
            c.execute("SELECT u.user_id, u.username, u.password, r.role_name, e.employee_name "
                      "FROM user_account u JOIN role r ON u.role_id = r.role_id "
                      "LEFT JOIN employee e ON u.employee_id = e.employee_id "
                      "WHERE u.username = %s AND u.is_active = true",
                      [data['username']])
            row = c.fetchone()
        if row:
            stored = row[2]
            if stored.startswith('pbkdf2_') or stored.startswith('bcrypt') or stored.startswith('argon2'):
                matched = check_password(data['password'], stored)
            else:
                matched = (data['password'] == stored)
                if matched:
                    hashed = make_password(data['password'])
                    with connection.cursor() as c:
                        c.execute("UPDATE user_account SET password = %s WHERE user_id = %s", [hashed, row[0]])
            if matched:
                return JsonResponse({'status': 'success', 'user': {
                    'id': row[0], 'username': row[1], 'role': row[3], 'name': row[4]}})
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
                      [data['username'], make_password(data['password'])])
            uid = c.fetchone()[0]
        return JsonResponse({'status': 'success', 'user_id': uid, 'message': 'Account created.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ================================================================
# HELPERS
# ================================================================
def _get_role(username):
    with connection.cursor() as c:
        c.execute("SELECT r.role_name FROM user_account u JOIN role r ON u.role_id = r.role_id WHERE u.username = %s AND u.is_active = true", [username])
        row = c.fetchone()
        return row[0] if row else None


# ================================================================
# USER MANAGEMENT (admin only)
# ================================================================
@csrf_exempt
def users_view(request):
    if request.method == 'GET':
        username = request.headers.get('X-Username')
        role = _get_role(username)
        if role != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        with connection.cursor() as c:
            c.execute("""SELECT u.user_id, u.username, r.role_name, COALESCE(e.employee_name, ''), u.is_active
                         FROM user_account u JOIN role r ON u.role_id = r.role_id
                         LEFT JOIN employee e ON u.employee_id = e.employee_id
                         ORDER BY u.user_id""")
            cols = ['id', 'username', 'role', 'employee_name', 'is_active']
            users = [dict(zip(cols, r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'users': users})

    if request.method == 'POST':
        username = request.headers.get('X-Username')
        role = _get_role(username)
        if role != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        try:
            data = json.loads(request.body)
            new_user = data.get('username')
            password = data.get('password')
            role_name = data.get('role', 'viewer')
            emp_name = data.get('employee_name', '')
            with connection.cursor() as c:
                c.execute("SELECT role_id FROM role WHERE role_name = %s", [role_name])
                rrow = c.fetchone()
                if not rrow:
                    return JsonResponse({'status': 'error', 'message': f'Invalid role: {role_name}'}, status=400)
                c.execute("SELECT user_id FROM user_account WHERE username = %s", [new_user])
                if c.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'Username already exists'}, status=409)
                eid = None
                if emp_name:
                    c.execute("SELECT employee_id FROM employee WHERE employee_name = %s", [emp_name])
                    e = c.fetchone()
                    if e:
                        eid = e[0]
                c.execute("INSERT INTO user_account (username, password, employee_id, role_id) VALUES (%s,%s,%s,%s) RETURNING user_id",
                          [new_user, make_password(password), eid, rrow[0]])
                uid = c.fetchone()[0]
            return JsonResponse({'status': 'success', 'user_id': uid, 'message': 'User created.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def user_detail_view(request, user_id):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    username = request.headers.get('X-Username')
    role = _get_role(username)
    if role != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    try:
        with connection.cursor() as c:
            c.execute("DELETE FROM user_account WHERE user_id = %s", [user_id])
        return JsonResponse({'status': 'success', 'message': 'User deleted.'})
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
@csrf_exempt
def inventory_data(request):
    if request.method == 'GET':
        try:
            with connection.cursor() as c:
                c.execute("""
                    SELECT i.inventory_id, rm.material_id, rm.material_name, i.quantity_on_hand,
                           i.reserved_qty, u.uom_code, i.lot_id, l.batch_no, l.expiry_date
                    FROM inventory i
                    JOIN raw_material rm ON i.material_id = rm.material_id
                    JOIN unit_of_measure u ON i.uom_id = u.uom_id
                    JOIN lot l ON i.lot_id = l.lot_id
                    ORDER BY rm.material_name
                """)
                cols = ['id', 'material_id', 'material', 'qty', 'reserved', 'uom', 'lot_id', 'lot', 'expiry']
                raw = [dict(zip(cols, r)) for r in c.fetchall()]
                c.execute("""
                    SELECT pi.product_inventory_id, p.product_id, p.product_name, pi.quantity_on_hand,
                           pi.reserved_qty, u.uom_code, pi.batch_id, pi.expiry_date
                    FROM product_inventory pi
                    JOIN product p ON pi.product_id = p.product_id
                    JOIN unit_of_measure u ON pi.uom_id = u.uom_id
                    ORDER BY p.product_name
                """)
                cols = ['id', 'product_id', 'product', 'qty', 'reserved', 'uom', 'batch', 'expiry']
                prod = [dict(zip(cols, r)) for r in c.fetchall()]
            return JsonResponse({'status': 'success', 'raw_materials': raw, 'finished_goods': prod})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if 'material_id' in data:
                with connection.cursor() as c:
                    c.execute(
                        "INSERT INTO inventory (material_id, lot_id, quantity_on_hand, uom_id) "
                        "VALUES (%s, %s, %s, %s) RETURNING inventory_id",
                        [data['material_id'], data.get('lot_id'), data['qty'], data['uom_id']]
                    )
                    iid = c.fetchone()[0]
                return JsonResponse({'status': 'success', 'inventory_id': iid, 'message': 'Raw material added.'})
            elif 'product_id' in data:
                with connection.cursor() as c:
                    c.execute(
                        "INSERT INTO product_inventory (product_id, batch_id, quantity_on_hand, uom_id, expiry_date) "
                        "VALUES (%s, %s, %s, %s, %s) RETURNING product_inventory_id",
                        [data['product_id'], data.get('batch'), data['qty'], data['uom_id'], data.get('expiry')]
                    )
                    pid = c.fetchone()[0]
                return JsonResponse({'status': 'success', 'product_inventory_id': pid, 'message': 'Finished good added.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Provide material_id (raw) or product_id (finished good)'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': f'Method {request.method} not supported'}, status=405)


@csrf_exempt
def inventory_item_view(request, item_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute("UPDATE inventory SET quantity_on_hand=%s, reserved_qty=%s WHERE inventory_id=%s",
                          [data.get('qty'), data.get('reserved', 0), item_id])
            return JsonResponse({'status': 'success', 'message': 'Updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM inventory WHERE inventory_id=%s", [item_id])
            return JsonResponse({'status': 'success', 'message': 'Deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def product_item_view(request, item_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute("UPDATE product_inventory SET quantity_on_hand=%s, reserved_qty=%s, expiry_date=%s WHERE product_inventory_id=%s",
                          [data.get('qty'), data.get('reserved', 0), data.get('expiry'), item_id])
            return JsonResponse({'status': 'success', 'message': 'Updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM product_inventory WHERE product_inventory_id=%s", [item_id])
            return JsonResponse({'status': 'success', 'message': 'Deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# PRODUCTION BATCHES
# ================================================================
@csrf_exempt
def batches_data(request):
    if request.method == 'GET':
        try:
            with connection.cursor() as c:
                c.execute("""
                    SELECT pb.batch_id, pb.product_id, p.product_name, pb.recipe_id, r.recipe_name,
                           pb.batch_date, pb.planned_qty, pb.actual_qty, pb.status, e.employee_name
                    FROM production_batch pb
                    JOIN product p ON pb.product_id = p.product_id
                    LEFT JOIN employee e ON pb.created_by = e.employee_id
                    LEFT JOIN recipe r ON pb.recipe_id = r.recipe_id
                    ORDER BY pb.batch_date DESC
                """)
                cols = ['id', 'product_id', 'product', 'recipe_id', 'recipe', 'date', 'planned', 'actual', 'status', 'created_by']
                batches = [dict(zip(cols, r)) for r in c.fetchall()]
            return JsonResponse({'status': 'success', 'batches': batches})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute(
                    "INSERT INTO production_batch (product_id, recipe_id, planned_qty, created_by, status) "
                    "VALUES (%s, %s, %s, %s, 'Planned') RETURNING batch_id",
                    [data['product_id'], data.get('recipe_id'), data['planned_qty'], data.get('created_by', 1)]
                )
                bid = c.fetchone()[0]
            return JsonResponse({'status': 'success', 'batch_id': bid, 'message': 'Batch created.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def batch_detail_view(request, batch_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            fields = []
            vals = []
            numeric_cols = {'actual_qty', 'planned_qty', 'product_id', 'recipe_id'}
            for k in ['status', 'actual_qty', 'planned_qty', 'product_id', 'recipe_id']:
                if k in data:
                    v = data[k]
                    if v == '' or v is None:
                        if k in numeric_cols:
                            v = None
                        else:
                            continue
                    fields.append(f'{k}=%s')
                    vals.append(v)
            if not fields:
                return JsonResponse({'status': 'error', 'message': 'No fields to update'}, status=400)
            vals.append(batch_id)
            with connection.cursor() as c:
                c.execute(f"UPDATE production_batch SET {', '.join(fields)} WHERE batch_id=%s", vals)
            return JsonResponse({'status': 'success', 'message': 'Batch updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM production_batch WHERE batch_id=%s", [batch_id])
            return JsonResponse({'status': 'success', 'message': 'Batch deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


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


@csrf_exempt
def qc_detail_view(request, qcid):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            fields = []
            vals = []
            for k in ['status', 'remarks', 'inspector_id']:
                if k in data:
                    fields.append(f'{k}=%s')
                    vals.append(data[k])
            if not fields:
                return JsonResponse({'status': 'error', 'message': 'No fields'}, status=400)
            vals.append(qcid)
            with connection.cursor() as c:
                c.execute(f"UPDATE quality_control SET {', '.join(fields)} WHERE qcid=%s", vals)
            return JsonResponse({'status': 'success', 'message': 'QC updated.'})
        except DatabaseError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM quality_control WHERE qcid=%s", [qcid])
            return JsonResponse({'status': 'success', 'message': 'QC deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# MACHINES
# ================================================================
@csrf_exempt
def machines_data(request):
    if request.method == 'GET':
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
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute(
                    "INSERT INTO machine (machine_name, machine_type, location, status, purchase_date) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING machine_id",
                    [data['name'], data.get('type', ''), data.get('location', ''),
                     data.get('status', 'Operational'), data.get('purchase_date')]
                )
                mid = c.fetchone()[0]
            return JsonResponse({'status': 'success', 'machine_id': mid, 'message': 'Machine added.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def machine_detail_view(request, machine_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            field_map = {'name': 'machine_name', 'type': 'machine_type'}
            set_cols = []
            set_vals = []
            for k, v in data.items():
                col = field_map.get(k, k)
                if col in ('machine_name','machine_type','location','status','purchase_date'):
                    set_cols.append(col)
                    set_vals.append(v)
            if not set_cols:
                return JsonResponse({'status': 'error', 'message': 'No fields'}, status=400)
            set_vals.append(machine_id)
            with connection.cursor() as c:
                c.execute(
                    f"UPDATE machine SET {', '.join(f'{k}=%s' for k in set_cols)} WHERE machine_id=%s", set_vals
                )
            return JsonResponse({'status': 'success', 'message': 'Machine updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM machine WHERE machine_id=%s", [machine_id])
            return JsonResponse({'status': 'success', 'message': 'Machine deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


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
@csrf_exempt
def purchasing_data(request):
    if request.method == 'GET':
        try:
            with connection.cursor() as c:
                c.execute("""
                    SELECT po.poid, po.supplier_id, s.supplier_name, po.order_date, po.status, po.total_amount,
                           (SELECT COUNT(*) FROM purchase_order_line pol WHERE pol.poid = po.poid) AS line_count
                    FROM purchase_order po
                    JOIN supplier s ON po.supplier_id = s.supplier_id
                    ORDER BY po.order_date DESC
                """)
                cols = ['id', 'supplier_id', 'supplier', 'date', 'status', 'total', 'lines']
                orders = [dict(zip(cols, r)) for r in c.fetchall()]
            return JsonResponse({'status': 'success', 'orders': orders})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute(
                    "INSERT INTO purchase_order (supplier_id, status, total_amount) "
                    "VALUES (%s, %s, %s) RETURNING poid",
                    [data['supplier_id'], data.get('status', 'Pending'), data.get('total', 0)]
                )
                poid = c.fetchone()[0]
            return JsonResponse({'status': 'success', 'poid': poid, 'message': 'PO created.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def purchasing_detail_view(request, poid):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            fields = [f'{k}=%s' for k in data if k in ('supplier_id','status','total_amount')]
            vals = [data[k] for k in data if k in ('supplier_id','status','total_amount')]
            if not fields:
                return JsonResponse({'status': 'error', 'message': 'No fields'}, status=400)
            vals.append(poid)
            with connection.cursor() as c:
                c.execute(f"UPDATE purchase_order SET {', '.join(fields)} WHERE poid=%s", vals)
            return JsonResponse({'status': 'success', 'message': 'PO updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM purchase_order WHERE poid=%s", [poid])
            return JsonResponse({'status': 'success', 'message': 'PO deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# SALES
# ================================================================
@csrf_exempt
def sales_data(request):
    if request.method == 'GET':
        try:
            with connection.cursor() as c:
                c.execute("""
                    SELECT so.sales_id, so.customer_id, c.customer_name, so.sale_date, so.status,
                           so.total_amount,
                           (SELECT COUNT(*) FROM sales_order_line sol WHERE sol.sales_id = so.sales_id) AS line_count
                    FROM sales_order so
                    JOIN customer c ON so.customer_id = c.customer_id
                    ORDER BY so.sale_date DESC
                """)
                cols = ['id', 'customer_id', 'customer', 'date', 'status', 'total', 'lines']
                orders = [dict(zip(cols, r)) for r in c.fetchall()]
            return JsonResponse({'status': 'success', 'orders': orders})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            with connection.cursor() as c:
                c.execute(
                    "INSERT INTO sales_order (customer_id, status, total_amount) "
                    "VALUES (%s, %s, %s) RETURNING sales_id",
                    [data['customer_id'], data.get('status', 'Pending'), data.get('total', 0)]
                )
                sid = c.fetchone()[0]
            return JsonResponse({'status': 'success', 'sales_id': sid, 'message': 'Sales order created.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


@csrf_exempt
def sales_detail_view(request, sales_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            fields = [f'{k}=%s' for k in data if k in ('customer_id','status','total_amount')]
            vals = [data[k] for k in data if k in ('customer_id','status','total_amount')]
            if not fields:
                return JsonResponse({'status': 'error', 'message': 'No fields'}, status=400)
            vals.append(sales_id)
            with connection.cursor() as c:
                c.execute(f"UPDATE sales_order SET {', '.join(fields)} WHERE sales_id=%s", vals)
            return JsonResponse({'status': 'success', 'message': 'Sales order updated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    if request.method == 'DELETE':
        try:
            with connection.cursor() as c:
                c.execute("DELETE FROM sales_order WHERE sales_id=%s", [sales_id])
            return JsonResponse({'status': 'success', 'message': 'Sales order deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# ================================================================
# REFERENCE DATA (for dropdowns)
# ================================================================
def ref_data(request):
    try:
        with connection.cursor() as c:
            c.execute("SELECT product_id, product_name FROM product WHERE is_active=true ORDER BY product_name")
            products = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT recipe_id, recipe_name FROM recipe ORDER BY recipe_name")
            recipes = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT employee_id, employee_name FROM employee ORDER BY employee_name")
            employees = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT supplier_id, supplier_name FROM supplier ORDER BY supplier_name")
            suppliers = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT customer_id, customer_name FROM customer ORDER BY customer_name")
            customers = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT uom_id, uom_code FROM unit_of_measure ORDER BY uom_code")
            uoms = [dict(zip(['id','code'], r)) for r in c.fetchall()]
            c.execute("SELECT material_id, material_name FROM raw_material ORDER BY material_name")
            materials = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT machine_id, machine_name FROM machine ORDER BY machine_name")
            machines = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT lot_id, batch_no FROM lot ORDER BY batch_no")
            lots = [dict(zip(['id','name'], r)) for r in c.fetchall()]
            c.execute("SELECT batch_id, batch_id AS name FROM production_batch ORDER BY batch_id")
            batches = [dict(zip(['id','name'], r)) for r in c.fetchall()]
        return JsonResponse({'status': 'success', 'data': {
            'products': products, 'recipes': recipes, 'employees': employees,
            'suppliers': suppliers, 'customers': customers, 'uoms': uoms,
            'materials': materials, 'machines': machines,
            'lots': lots, 'batches': batches,
        }})
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
                c.execute("INSERT INTO user_account (username, password, role_id) VALUES (%s, 'test', 1)",
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
