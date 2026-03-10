# =====================================================
# PARTE 1 - CONFIGURACIÓN Y BASE DE DATOS
# =====================================================

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

DB_NAME = "pos_pro.db"
MONEDA_BASE = "CUP"


def get_connection():
    return sqlite3.connect(DB_NAME)


def inicializar_db():
    conn = get_connection()
    cursor = conn.cursor()

    # PRODUCTOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL,
        stock_minimo INTEGER DEFAULT 5
    )
    """)

    # MONEDAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monedas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        tasa REAL NOT NULL
    )
    """)

    # VENTAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        total REAL NOT NULL,
        moneda TEXT NOT NULL,
        metodo_pago TEXT NOT NULL,
        terminal_id TEXT DEFAULT 'TERMINAL_1'
    )
    """)
    # Asegurar compatibilidad con bases de datos existentes: agregar columna terminal_id si falta
    cursor.execute("PRAGMA table_info(ventas)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'terminal_id' not in cols:
        try:
            cursor.execute("ALTER TABLE ventas ADD COLUMN terminal_id TEXT DEFAULT 'TERMINAL_1'")
        except Exception:
            pass

    # Monedas por defecto
    monedas_default = {
        "CUP": 1.0,
        "EUR": 340.0,
        "USD": 500.0,
        "MLC": 300.0,
        "TARJETA CLASICA": 300.0  
    }

    for nombre, tasa in monedas_default.items():
        cursor.execute(
            "INSERT OR IGNORE INTO monedas (nombre, tasa) VALUES (?, ?)",
            (nombre, tasa)
        )

    # USUARIOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL
    )
    """)

    # Usuario administrador por defecto
    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (username, password, rol)
        VALUES ('admin', 'admin123', 'Admin')
    """)

    # REPORTES (histórico)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reportes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        contenido TEXT NOT NULL
    )
    """)

    # CONFIGURACIÓN GENERAL
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clave TEXT UNIQUE NOT NULL,
        valor TEXT NOT NULL
    )
    """)

    # Terminal ID por defecto
    cursor.execute(
        "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('terminal_id', 'TERMINAL_1')"
    )

    # PERMISOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permiso TEXT UNIQUE NOT NULL,
        descripcion TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuario_permisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        permiso_id INTEGER NOT NULL
    )
    """)

    # Permisos por defecto
    permisos_default = [
        ("manage_products", "Gestionar productos e inventario"),
        ("close_cash", "Cerrar/abrir caja"),
        ("view_reports", "Ver reportes"),
        ("manage_users", "Gestionar usuarios y permisos")
    ]

    for perm, desc in permisos_default:
        cursor.execute(
            "INSERT OR IGNORE INTO permisos (permiso, descripcion) VALUES (?, ?)",
            (perm, desc)
        )

    # =====================================================
    # COMPRAS Y PROVEEDORES
    # =====================================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        contacto TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        proveedor_id INTEGER,
        total REAL,
        moneda TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compra_id INTEGER,
        producto_id INTEGER,
        cantidad INTEGER,
        precio_unitario REAL,
        subtotal REAL
    )
    """)

    # Tablas adicionales necesarias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS denominaciones_billetes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valor REAL NOT NULL UNIQUE,
        nombre TEXT,
        activo INTEGER DEFAULT 1
    )
    """)
    # si la tabla está vacía insertamos algunas denominaciones comunes
    cursor.execute("SELECT COUNT(*) FROM denominaciones_billetes")
    if cursor.fetchone()[0] == 0:
        for val, name in [(1, "1 CUP"), (3, "3 CUP"), (5, "5 CUP"), (10, "10 CUP"),
                          (20, "20 CUP"), (50, "50 CUP"), (100, "100 CUP"),
                          (200, "200 CUP"), (500, "500 CUP")]:
            cursor.execute(
                "INSERT OR IGNORE INTO denominaciones_billetes (valor, nombre, activo) VALUES (?, ?, 1)",
                (val, name)
            )


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_apertura TEXT,
        fecha_cierre TEXT,
        fondo_inicial REAL,
        total_ventas REAL DEFAULT 0,
        abierta INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS balance_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caja_id INTEGER,
        denominacion REAL,
        cantidad INTEGER,
        subtotal REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        cantidad INTEGER,
        subtotal REAL
    )
    """)

    conn.commit()
    conn.close()


def obtener_monedas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM monedas")
    monedas = [m[0] for m in cursor.fetchall()]
    conn.close()
    return monedas


def obtener_tasa(moneda):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tasa FROM monedas WHERE nombre=?", (moneda,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return float(resultado[0])
    return 1.0


def obtener_denominaciones_billetes():
    """Obtiene todas las denominaciones de billetes activas"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, valor, nombre FROM denominaciones_billetes WHERE activo = 1 ORDER BY valor DESC")
    denominaciones = cursor.fetchall()
    conn.close()
    return denominaciones


def obtener_terminal_id():
    """Obtiene el ID de la terminal/caja"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'terminal_id'")
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else "TERMINAL_1"


def obtener_productos_stock_critico():
    """Retorna productos con stock en nivel crítico"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, stock, stock_minimo 
        FROM productos 
        WHERE stock <= stock_minimo 
        ORDER BY stock ASC
    """)
    productos = cursor.fetchall()
    conn.close()
    return productos


def obtener_estadisticas_hoy():
    """Obtiene estadísticas del día actual"""
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total de ventas hoy
    cursor.execute("SELECT SUM(total) FROM ventas WHERE fecha LIKE ?", (f"{hoy}%",))
    total_ventas = cursor.fetchone()[0] or 0
    
    # Cantidad de transacciones
    cursor.execute("SELECT COUNT(*) FROM ventas WHERE fecha LIKE ?", (f"{hoy}%",))
    num_transacciones = cursor.fetchone()[0]
    
    # Producto más vendido
    cursor.execute("""
        SELECT p.nombre, SUM(dv.cantidad) as total_qty
        FROM detalle_venta dv
        JOIN ventas v ON dv.venta_id = v.id
        JOIN productos p ON dv.producto_id = p.id
        WHERE v.fecha LIKE ?
        GROUP BY p.id
        ORDER BY total_qty DESC
        LIMIT 1
    """, (f"{hoy}%",))
    mas_vendido = cursor.fetchone()
    
    # Métodos de pago
    cursor.execute("""
        SELECT metodo_pago, COUNT(*) as cantidad, SUM(total) as monto
        FROM ventas
        WHERE fecha LIKE ?
        GROUP BY metodo_pago
    """, (f"{hoy}%",))
    metodos_pago = cursor.fetchall()
    
    conn.close()
    
    return {
        "total_ventas": float(total_ventas),
        "num_transacciones": num_transacciones,
        "mas_vendido": mas_vendido,
        "metodos_pago": metodos_pago
    }


def obtener_estadisticas_periodo(dias=7):
    """Obtiene estadísticas de los últimos N días"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT DATE(fecha) as dia, SUM(total) as total_dia
        FROM ventas
        WHERE fecha >= datetime('now', '-{dias} days')
        GROUP BY DATE(fecha)
        ORDER BY dia DESC
    """)
    
    datos = cursor.fetchall()
    conn.close()
    return datos


def convertir_moneda(monto_base, moneda_destino):
    """
    Convierte desde moneda base (CUP) a otra moneda
    """
    tasa = obtener_tasa(moneda_destino)
    if tasa == 0:
        return 0
    return monto_base / tasa


def convertir_a_cup(monto, moneda_origen):
    """Convierte un monto desde `moneda_origen` a CUP usando la tasa (CUP por unidad de moneda)."""
    tasa = obtener_tasa(moneda_origen)
    try:
        return float(monto) * float(tasa)
    except Exception:
        return 0.0


def caja_abierta():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT abierta FROM caja ORDER BY id DESC LIMIT 1")
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return resultado[0] == 1
    return False


def abrir_caja(fondo_inicial):
    conn = get_connection()
    cursor = conn.cursor()

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO caja (fecha_apertura, fondo_inicial, total_ventas, abierta)
        VALUES (?, ?, 0, 1)
    """, (fecha, float(fondo_inicial)))

    conn.commit()
    conn.close()

def registrar_total_en_caja(monto):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE caja
        SET total_ventas = total_ventas + ?
        WHERE abierta = 1
    """, (float(monto),))

    conn.commit()
    conn.close()


def cerrar_caja():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, fondo_inicial, total_ventas
        FROM caja
        WHERE abierta = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    caja = cursor.fetchone()

    if not caja:
        conn.close()
        return None

    caja_id, fondo, total = caja
    fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE caja
        SET fecha_cierre = ?, abierta = 0
        WHERE id = ?
    """, (fecha_cierre, caja_id))

    conn.commit()
    conn.close()

    total_final = float(fondo) + float(total)

    return {
        "fondo_inicial": float(fondo),
        "total_ventas": float(total),
        "total_en_caja": total_final
    }


# ---------------- REPORTES AUXILIARES ----------------

def total_vendido_hoy():
    conn = get_connection()
    cursor = conn.cursor()

    hoy = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT SUM(total)
        FROM ventas
        WHERE fecha LIKE ?
    """, (f"{hoy}%",))

    resultado = cursor.fetchone()[0]
    conn.close()

    return float(resultado) if resultado else 0.0


def total_por_metodo(metodo):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(total)
        FROM ventas
        WHERE metodo_pago = ?
    """, (metodo,))

    resultado = cursor.fetchone()[0]
    conn.close()

    return float(resultado) if resultado else 0.0


def guardar_reporte(tipo, contenido):
    """Guarda un reporte en la tabla `reportes` con timestamp."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO reportes (fecha, tipo, contenido) VALUES (?, ?, ?)",
            (fecha, tipo, contenido)
        )
        conn.commit()
    finally:
        conn.close()
# =====================================================
# SISTEMA DINÁMICO DE DENOMINACIONES
# =====================================================

def obtener_denominaciones(moneda):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, valor, nombre
        FROM denominaciones_billetes
        WHERE activo = 1
        ORDER BY valor DESC
    """)
    datos = cursor.fetchall()
    conn.close()
    return datos


def agregar_proveedor_db(nombre, contacto=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO proveedores (nombre, contacto) VALUES (?, ?)",
            (nombre, contacto)
        )
        conn.commit()
    finally:
        conn.close()


def obtener_proveedores():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, contacto FROM proveedores ORDER BY nombre ASC")
    datos = cursor.fetchall()
    conn.close()
    return datos


def eliminar_proveedor_db(proveedor_id):
    """Elimina un proveedor de la base de datos"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM proveedores WHERE id=?", (proveedor_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def registrar_compra_db(proveedor_id, items, moneda=MONEDA_BASE):
    """Registra una compra y actualiza stock.

    items: lista de dicts {'producto_id': int, 'cantidad': int, 'precio_unitario': float}
    """
    conn = get_connection()
    cursor = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = sum(i['cantidad'] * float(i['precio_unitario']) for i in items)

    cursor.execute(
        "INSERT INTO compras (fecha, proveedor_id, total, moneda) VALUES (?, ?, ?, ?)",
        (fecha, proveedor_id, float(total), moneda)
    )
    compra_id = cursor.lastrowid

    for it in items:
        producto_id = int(it['producto_id'])
        cantidad = int(it['cantidad'])
        precio = float(it['precio_unitario'])
        subtotal = cantidad * precio

        cursor.execute(
            "INSERT INTO detalle_compra (compra_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
            (compra_id, producto_id, cantidad, precio, subtotal)
        )

        # Actualizar stock del producto si existe
        cursor.execute("SELECT stock FROM productos WHERE id=?", (producto_id,))
        row = cursor.fetchone()
        if row is not None:
            nuevo_stock = row[0] + cantidad
            cursor.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, producto_id))

    conn.commit()
    conn.close()


def obtener_historial_compras(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id, c.fecha, p.nombre, c.total, c.moneda FROM compras c LEFT JOIN proveedores p ON c.proveedor_id = p.id ORDER BY c.id DESC LIMIT ?",
        (limit,)
    )
    datos = cursor.fetchall()
    conn.close()
    return datos


def agregar_denominacion_db(valor, nombre):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO denominaciones_billetes (valor, nombre, activo)
            VALUES (?, ?, 1)
        """, (float(valor), nombre))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def eliminar_denominacion_db(denominacion_id):
    """Elimina (desactiva) una denominación de billetes"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE denominaciones_billetes SET activo=0 WHERE id=?", (denominacion_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def eliminar_moneda_db(moneda_nombre):
    """Elimina una moneda de la base de datos, CUP no puede eliminarse"""
    if moneda_nombre == "CUP":
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM monedas WHERE nombre=?", (moneda_nombre,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# =====================================================
# VENTANA GESTIÓN DE DENOMINACIONES
# =====================================================
# Nota: la gestión de denominaciones ahora está implementada
# como método `gestion_denominaciones` dentro de la clase `POS`.
# Se eliminó la versión global duplicada para evitar conflictos.


# =====================================================
# GENERADOR DINÁMICO DE EFECTIVO
# =====================================================

def generar_panel_efectivo(self, ventana, total_esperado):

    denominaciones = obtener_denominaciones(MONEDA_BASE)

    self.vars_billetes = {}

    frame = tk.Frame(ventana)
    frame.pack(fill="both", expand=True)

    label_total = tk.Label(ventana, text="Total contado: 0.00", font=("Arial", 12, "bold"))
    label_total.pack(pady=5)

    label_diff = tk.Label(ventana, text="Diferencia: 0.00", font=("Arial", 11))
    label_diff.pack()

    def actualizar_total():
        total = 0
        for valor, var in self.vars_billetes.items():
            total += valor * var.get()

        diferencia = total - total_esperado

        label_total.config(text=f"Total contado: {total:.2f} CUP")
        label_diff.config(text=f"Diferencia: {diferencia:.2f} CUP")

    for bid, valor, nombre in denominaciones:

        row = tk.Frame(frame)
        row.pack(fill="x", pady=2)

        tk.Label(row, text=f"{nombre}", width=20, anchor="w").pack(side="left")

        var = tk.IntVar(value=0)
        self.vars_billetes[valor] = var

        spin = tk.Spinbox(
            row,
            from_=0,
            to=1000,
            width=8,
            textvariable=var,
            command=actualizar_total
        )
        spin.pack(side="left")

        var.trace_add("write", lambda *args: actualizar_total())

# =====================================================
# PARTE 3 - CLASE PRINCIPAL POS (ESTRUCTURA BASE UI)
# =====================================================

class POS(tk.Tk):

    def __init__(self, usuario=None, rol=None):
        super().__init__()

        self.usuario = usuario
        self.rol = rol
        self.terminal_id = obtener_terminal_id()

        self.title("POS Profesional")
        self.geometry("1300x750")
        self.configure(bg="#f4f6f9")

        # Variables principales
        self.carrito = []
        self.moneda_actual = tk.StringVar(value=MONEDA_BASE)
        self.termino_busqueda = tk.StringVar()
        self.lista_productos_sugeridos = {}

        # Construcción UI
        self.crear_menu()
        self.crear_layout()

        # Cargar datos
        self.cargar_productos()

        # Validar caja
        if not caja_abierta():
            self.ventana_apertura_caja()
        
        # Mostrar notificaciones de stock crítico
        self.mostrar_notificaciones_stock_critico()


    # =====================================================
    # MENÚ SUPERIOR
    # =====================================================

    def crear_menu(self):

        barra = tk.Menu(self)

        # Inventario
        menu_inv = tk.Menu(barra, tearoff=0)
        menu_inv.add_command(label="Gestión de Inventario", command=self.gestion_inventario)
        barra.add_cascade(label="Inventario", menu=menu_inv)

        # Compras
        menu_compras = tk.Menu(barra, tearoff=0)
        menu_compras.add_command(label="Nueva Compra", command=self.ventana_nueva_compra)
        menu_compras.add_command(label="Proveedores", command=self.gestionar_proveedores)
        menu_compras.add_command(label="Historial de Compras", command=self.historial_compras)
        barra.add_cascade(label="Compras", menu=menu_compras)
        
        # Administración
        # Solo mostrar opciones administrativas si el usuario es Admin
        if getattr(self, 'rol', None) == 'Admin':
            menu_admin = tk.Menu(barra, tearoff=0)
            menu_admin.add_command(label="Editar Tasas", command=self.editar_tasas)
            menu_admin.add_command(label="Reporte del Día", command=self.reporte_dia)
            menu_admin.add_command(label="Balance de Caja", command=self.balance_caja_manual)
            menu_admin.add_command(label="Denominaciones", command=self.gestion_denominaciones)
            barra.add_cascade(label="Administración", menu=menu_admin)

        # Caja (disponible para todos)
        menu_caja = tk.Menu(barra, tearoff=0)
        menu_caja.add_command(label="Abrir Caja", command=self.ventana_apertura_caja)
        menu_caja.add_command(label="Cerrar Caja", command=self.cerrar_caja_ui)
        barra.add_cascade(label="Caja", menu=menu_caja)

        # Historial de reportes
        menu_reportes = tk.Menu(barra, tearoff=0)
        menu_reportes.add_command(label="Histórico de reportes", command=self.mostrar_historico_reportes)
        menu_reportes.add_command(label="Dashboard", command=self.mostrar_dashboard)
        barra.add_cascade(label="Reportes", menu=menu_reportes)

        # Usuario
        menu_usuario = tk.Menu(barra, tearoff=0)
        menu_usuario.add_command(label="Cambiar Usuario", command=self.cambiar_usuario)
        if getattr(self, 'rol', None) == 'Admin':
            menu_usuario.add_separator()
            menu_usuario.add_command(label="Gestionar Usuarios", command=self.gestion_usuarios)
        barra.add_cascade(label="Usuario", menu=menu_usuario)

        self.config(menu=barra)

    # =====================================================
    # MENÚ COMPRAS - MÉTODOS
    # =====================================================

    def ventana_nueva_compra(self):
        ventana = tk.Toplevel(self)
        ventana.title("Nueva Compra")
        ventana.geometry("700x500")

        # Proveedor
        proveedores = obtener_proveedores()
        prov_nombres = [p[1] for p in proveedores]
        prov_map = {p[1]: p[0] for p in proveedores}

        frame_top = tk.Frame(ventana)
        frame_top.pack(fill="x", padx=10, pady=10)

        tk.Label(frame_top, text="Proveedor:").pack(side="left")
        prov_var = tk.StringVar()
        combo_prov = ttk.Combobox(frame_top, values=prov_nombres, textvariable=prov_var, state="readonly", width=30)
        combo_prov.pack(side="left", padx=5)

        # Producto y líneas
        frame_linea = tk.Frame(ventana)
        frame_linea.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_linea, text="Producto:").grid(row=0, column=0)
        productos = []
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, precio FROM productos ORDER BY nombre")
        for pid, nombre, precio in cur.fetchall():
            productos.append((pid, nombre, precio))
        conn.close()

        prod_map = {n: pid for pid, n, _ in productos}
        prod_names = [n for _, n, _ in productos]

        prod_var = tk.StringVar()
        combo_prod = ttk.Combobox(frame_linea, values=prod_names, textvariable=prod_var, state="readonly", width=30)
        combo_prod.grid(row=0, column=1, padx=5)

        tk.Label(frame_linea, text="Cantidad:").grid(row=0, column=2)
        entry_cant = tk.Entry(frame_linea, width=6)
        entry_cant.grid(row=0, column=3, padx=5)
        entry_cant.insert(0, "1")

        tk.Label(frame_linea, text="Precio Unit:").grid(row=0, column=4)
        entry_prec = tk.Entry(frame_linea, width=10)
        entry_prec.grid(row=0, column=5, padx=5)

        tree = ttk.Treeview(ventana, columns=("Producto", "Cant", "Precio", "Subtotal"), show="headings", height=10)
        for c, t in [("Producto", 300), ("Cant", 60), ("Precio", 80), ("Subtotal", 100)]:
            tree.heading(c, text=c)
            tree.column(c, width=t)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        items = []

        def agregar_linea():
            nombre = prod_var.get()
            if not nombre:
                messagebox.showwarning("Validación", "Selecciona un producto")
                return
            try:
                cantidad = int(entry_cant.get())
                precio = float(entry_prec.get())
            except Exception:
                messagebox.showwarning("Validación", "Cantidad o precio inválido")
                return

            pid = prod_map.get(nombre)
            subtotal = cantidad * precio
            items.append({"producto_id": pid, "cantidad": cantidad, "precio_unitario": precio})
            tree.insert("", "end", values=(nombre, cantidad, f"{precio:.2f}", f"{subtotal:.2f}"))
            entry_cant.delete(0, "end"); entry_cant.insert(0, "1")
            entry_prec.delete(0, "end")

        def registrar_compra():
            prov_name = prov_var.get()
            if not prov_name:
                messagebox.showwarning("Validación", "Selecciona un proveedor")
                return
            if not items:
                messagebox.showwarning("Validación", "Agrega al menos una línea")
                return
            prov_id = prov_map.get(prov_name)
            try:
                registrar_compra_db(prov_id, items, moneda=self.moneda_actual.get())
                messagebox.showinfo("Éxito", "Compra registrada")
                # Refrescar lista de productos en la UI principal
                try:
                    self.cargar_productos()
                except Exception:
                    pass
                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        frame_acc = tk.Frame(ventana)
        frame_acc.pack(fill="x", padx=10, pady=5)

        tk.Button(frame_acc, text="Agregar línea", command=agregar_linea, bg="#007bff", fg="white").pack(side="left", padx=5)
        tk.Button(frame_acc, text="Registrar Compra", command=registrar_compra, bg="#28a745", fg="white").pack(side="right", padx=5)


    def ventana_recepcion_mercancia(self):
        # Por ahora alias a nueva compra (puede modificarse para flujos distintos)
        self.ventana_nueva_compra()

    def gestionar_proveedores(self):
        ventana = tk.Toplevel(self)
        ventana.title("Gestionar Proveedores")
        ventana.geometry("500x400")

        # Treeview para listar proveedores
        tree_proveedores = ttk.Treeview(ventana, columns=("ID", "Nombre", "Contacto"), show="headings")
        for col, width in [("ID", 50), ("Nombre", 200), ("Contacto", 200)]:
            tree_proveedores.heading(col, text=col)
            tree_proveedores.column(col, width=width)
        tree_proveedores.pack(fill="both", expand=True, padx=10, pady=10)

        conn = get_connection()
        cursor = conn.cursor()

        def cargar_proveedores():
            for row in tree_proveedores.get_children():
                tree_proveedores.delete(row)
            cursor.execute("SELECT id, nombre, contacto FROM proveedores ORDER BY nombre")
            for row in cursor.fetchall():
                tree_proveedores.insert("", "end", values=row)

        def eliminar_proveedor():
            seleccionado = tree_proveedores.selection()
            if not seleccionado:
                messagebox.showwarning("Aviso", "Seleccione un proveedor para eliminar")
                return
            proveedor_id = tree_proveedores.item(seleccionado)["values"][0]
            confirmar = messagebox.askyesno("Confirmar", "¿Desea eliminar este proveedor?")
            if not confirmar:
                return
            if eliminar_proveedor_db(proveedor_id):
                cargar_proveedores()
                messagebox.showinfo("Éxito", "Proveedor eliminado correctamente")
            else:
                messagebox.showerror("Error", "No se pudo eliminar el proveedor")

        frame_botones = tk.Frame(ventana)
        frame_botones.pack(fill="x", padx=10, pady=5)
        btn_eliminar_proveedor = tk.Button(frame_botones, text="Eliminar Proveedor", command=eliminar_proveedor)
        btn_eliminar_proveedor.pack(side="left", padx=5)

        # Formulario para agregar proveedor
        frame = tk.Frame(ventana)
        frame.pack(fill="x", padx=10, pady=5)

        tk.Label(frame, text="Nombre:").grid(row=0, column=0)
        e_nombre = tk.Entry(frame, width=30)
        e_nombre.grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Contacto:").grid(row=1, column=0)
        e_contacto = tk.Entry(frame, width=30)
        e_contacto.grid(row=1, column=1, padx=5)

        def agregar():
            nombre = e_nombre.get().strip()
            contacto = e_contacto.get().strip()
            if not nombre:
                messagebox.showwarning("Validación", "Nombre requerido")
                return
            agregar_proveedor_db(nombre, contacto)
            e_nombre.delete(0, "end")
            e_contacto.delete(0, "end")
            cargar_proveedores()

        tk.Button(frame, text="Agregar", command=agregar, bg="#28a745", fg="white").grid(row=2, column=1, sticky="e", pady=5)

        cargar_proveedores()


    def historial_compras(self):
        ventana = tk.Toplevel(self)
        ventana.title("Historial de Compras")
        ventana.geometry("700x400")

        tree = ttk.Treeview(ventana, columns=("ID", "Fecha", "Proveedor", "Total", "Moneda"), show="headings")
        for c, w in [("ID", 50), ("Fecha", 180), ("Proveedor", 200), ("Total", 100), ("Moneda", 80)]:
            tree.heading(c, text=c)
            tree.column(c, width=w)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for cid, fecha, proveedor, total, moneda in obtener_historial_compras():
            tree.insert("", "end", values=(cid, fecha, proveedor or "-", f"{total:.2f}", moneda))

    # =====================================================
    # LAYOUT PRINCIPAL
    # =====================================================

    def crear_layout(self):

        contenedor = tk.Frame(self, bg="#f4f6f9")
        contenedor.pack(fill="both", expand=True)

        # ================= PANEL PRODUCTOS =================
        self.panel_productos = tk.Frame(contenedor, bg="white")
        self.panel_productos.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            self.panel_productos,
            text="Productos",
            font=("Arial", 18, "bold"),
            bg="white"
        ).pack(pady=10)

        # Mostrar usuario actual si existe
        if getattr(self, 'usuario', None):
            tk.Label(
                self.panel_productos,
                text=f"Usuario: {self.usuario} | Rol: {self.rol or 'N/A'}",
                bg="white",
                font=("Arial", 10)
            ).pack()

        # Selector de moneda
        frame_moneda = tk.Frame(self.panel_productos, bg="white")
        frame_moneda.pack(pady=5)

        tk.Label(frame_moneda, text="Moneda:", bg="white").pack(side="left")

        self.combo_moneda = ttk.Combobox(
            frame_moneda,
            textvariable=self.moneda_actual,
            values=obtener_monedas(),
            state="readonly",
            width=10
        )
        self.combo_moneda.pack(side="left", padx=5)
        self.combo_moneda.bind("<<ComboboxSelected>>", lambda e: self.actualizar_total())

        # Buscador de productos
        frame_busqueda = tk.Frame(self.panel_productos, bg="white")
        frame_busqueda.pack(pady=10, padx=10, fill="x")

        tk.Label(frame_busqueda, text="Buscar:", bg="white", font=("Arial", 10)).pack(side="left", padx=5)

        entry_busqueda = tk.Entry(frame_busqueda, textvariable=self.termino_busqueda, font=("Arial", 10), width=25)
        entry_busqueda.pack(side="left", padx=5, fill="x", expand=True)
        entry_busqueda.bind("<KeyRelease>", lambda e: self.cargar_productos())

        tk.Button(
            frame_busqueda,
            text="Limpiar",
            command=lambda: (self.termino_busqueda.set(""), self.cargar_productos()),
            bg="#6c757d",
            fg="white",
            font=("Arial", 9)
        ).pack(side="left", padx=5)

        # Canvas para mostrar productos como botones
        self.canvas_productos = tk.Canvas(self.panel_productos, bg="white", highlightthickness=0)
        self.canvas_productos.pack(fill="both", expand=True, padx=10, pady=10)

        self.scrollbar_canvas = ttk.Scrollbar(self.panel_productos, orient="vertical", command=self.canvas_productos.yview)
        self.scrollbar_canvas.pack(side="right", fill="y")

        self.canvas_productos.configure(yscrollcommand=self.scrollbar_canvas.set)

        self.frame_productos = tk.Frame(self.canvas_productos, bg="white")
        self.canvas_window = self.canvas_productos.create_window((0, 0), window=self.frame_productos, anchor="nw")

        def on_canvas_configure(event):
            self.canvas_productos.configure(scrollregion=self.canvas_productos.bbox("all"))

        self.frame_productos.bind("<Configure>", on_canvas_configure)

        # ================= PANEL VENTA =================
        self.panel_venta = tk.Frame(contenedor, bg="#e9ecef", width=380)
        self.panel_venta.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(
            self.panel_venta,
            text="Venta Actual",
            font=("Arial", 16, "bold"),
            bg="#e9ecef"
        ).pack(pady=10)

        # ===== FRAME PARA BUSCAR Y AGREGAR PRODUCTOS =====
        frame_buscar_producto = tk.Frame(self.panel_venta, bg="#e9ecef")
        frame_buscar_producto.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_buscar_producto, text="Producto:", bg="#e9ecef", font=("Arial", 9)).pack(side="left", padx=5)
        
        self.entry_producto = tk.Entry(frame_buscar_producto, font=("Arial", 10), width=20)
        self.entry_producto.pack(side="left", padx=5, fill="x", expand=True)
        self.entry_producto.bind("<KeyRelease>", self.actualizar_sugerencias)
        self.entry_producto.bind("<Return>", self.agregar_desde_campo_texto)
        
        tk.Label(frame_buscar_producto, text="Qty:", bg="#e9ecef", font=("Arial", 9)).pack(side="left", padx=5)
        self.entry_cantidad = tk.Entry(frame_buscar_producto, width=5, font=("Arial", 10))
        self.entry_cantidad.insert(0, "1")
        self.entry_cantidad.pack(side="left", padx=5)

        # Listbox de sugerencias
        tk.Label(
            self.panel_venta,
            text="Sugerencias:",
            bg="#e9ecef",
            font=("Arial", 9)
        ).pack(pady=(10, 0), padx=10, anchor="w")

        self.listbox_sugerencias = tk.Listbox(self.panel_venta, height=4, font=("Arial", 9))
        self.listbox_sugerencias.pack(fill="x", padx=10, pady=5)
        self.listbox_sugerencias.bind("<Double-Button-1>", self.seleccionar_sugerencia)
        self.listbox_sugerencias.bind("<Return>", self.seleccionar_sugerencia)

        # Lista de venta
        tk.Label(
            self.panel_venta,
            text="Items:",
            bg="#e9ecef",
            font=("Arial", 9)
        ).pack(pady=(10, 0), padx=10, anchor="w")

        self.lista_venta = tk.Listbox(self.panel_venta, height=12, font=("Arial", 9))
        self.lista_venta.pack(fill="both", expand=True, padx=10, pady=5)

        self.label_total = tk.Label(
            self.panel_venta,
            text="Total: 0.00 CUP",
            font=("Arial", 14, "bold"),
            bg="#e9ecef"
        )
        self.label_total.pack(pady=5)

        tk.Button(
            self.panel_venta,
            text="Eliminar selección",
            bg="#dc3545",
            fg="white",
            font=("Arial", 10),
            command=self.eliminar_item_venta
        ).pack(fill="x", padx=15, pady=(0,5))

        tk.Button(
            self.panel_venta,
            text="Finalizar Venta",
            bg="#28a745",
            fg="white",
            font=("Arial", 12, "bold"),
            command=self.finalizar_venta
        ).pack(fill="x", padx=15, pady=10)

    # =====================================================
    # CARGAR PRODUCTOS
    # =====================================================

    def cargar_productos(self):
        # Limpiar frame anterior
        for widget in self.frame_productos.winfo_children():
            widget.destroy()

        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener término de búsqueda
        termino = self.termino_busqueda.get().strip().lower()
        
        cursor.execute("SELECT id, nombre, precio, stock, stock_minimo FROM productos")
        todos_productos = cursor.fetchall()
        conn.close()
        
        # Filtrar productos según término de búsqueda
        if termino:
            productos = [p for p in todos_productos if termino in p[1].lower()]
        else:
            productos = todos_productos

        # Crear grilla de botones para productos
        for idx, (producto_id, nombre, precio, stock, stock_min) in enumerate(productos):
            row = idx // 2
            col = idx % 2

            # Color según stock
            bg_color = "#ffe5e5" if stock <= stock_min else "#e8f5e9"

            frame_producto = tk.Frame(self.frame_productos, bg=bg_color, relief="solid", borderwidth=2)
            frame_producto.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

            tk.Label(frame_producto, text=nombre, font=("Arial", 12, "bold"), bg=bg_color).pack(pady=5)
            tk.Label(frame_producto, text=f"Precio: {precio:.2f} CUP", font=("Arial", 10), bg=bg_color).pack()
            tk.Label(frame_producto, text=f"Stock: {stock}", font=("Arial", 10), bg=bg_color).pack()

            btn = tk.Button(
                frame_producto,
                text="Agregar",
                command=lambda pid=producto_id, n=nombre, p=precio, s=stock: self.agregar_producto_desde_canvas(pid, n, p, s),
                bg="#28a745",
                fg="white",
                font=("Arial", 10)
            )
            btn.pack(pady=5, padx=5, fill="x")

        self.canvas_productos.configure(scrollregion=self.canvas_productos.bbox("all"))

    def agregar_producto_desde_canvas(self, producto_id, nombre, precio, stock):
        # leer cantidad deseada desde la entrada
        try:
            cantidad_deseada = int(self.entry_cantidad.get())
            if cantidad_deseada <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Error", "Cantidad inválida")
            return

        if stock <= 0:
            messagebox.showwarning("Sin stock", "Producto sin disponibilidad")
            return

        # Verificar si ya está en carrito
        for item in self.carrito:
            if item["id"] == producto_id:
                if item["cantidad"] + cantidad_deseada <= stock:
                    item["cantidad"] += cantidad_deseada
                else:
                    messagebox.showwarning("Stock límite", "No hay suficientes unidades disponibles")
                self.actualizar_lista_venta()
                return

        # Si no existe en carrito
        if cantidad_deseada > stock:
            messagebox.showwarning("Stock límite", "No hay suficientes unidades disponibles")
            return

        self.carrito.append({
            "id": producto_id,
            "nombre": nombre,
            "precio": float(precio),
            "cantidad": cantidad_deseada
        })

        self.actualizar_lista_venta()

    def actualizar_sugerencias(self, event=None):
        """Actualiza el listbox de sugerencias según el texto ingresado"""
        termino = self.entry_producto.get().strip().lower()
        self.listbox_sugerencias.delete(0, "end")

        if not termino or len(termino) < 1:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE LOWER(nombre) LIKE ?", (f"%{termino}%",))
        productos = cursor.fetchall()
        conn.close()

        # Mostrar sugerencias con formato: "nombre - precio"
        self.lista_productos_sugeridos = {}  # Guardar para referencia
        for producto_id, nombre, precio, stock in productos:
            if stock > 0:  # Solo mostrar productos con stock
                display_text = f"{nombre} - ${precio:.2f}"
                self.listbox_sugerencias.insert("end", display_text)
                self.lista_productos_sugeridos[display_text] = {
                    "id": producto_id,
                    "nombre": nombre,
                    "precio": precio,
                    "stock": stock
                }

    def seleccionar_sugerencia(self, event=None):
        """Selecciona una sugerencia y la agrega al carrito"""
        selection = self.listbox_sugerencias.curselection()
        if not selection:
            return

        idx = selection[0]
        item_text = self.listbox_sugerencias.get(idx)

        if item_text in self.lista_productos_sugeridos:
            producto = self.lista_productos_sugeridos[item_text]
            self.agregar_producto_desde_campo_texto(producto)

    def agregar_desde_campo_texto(self, event=None):
        """Agrega producto desde el campo de texto si hay un ítem único"""
        termino = self.entry_producto.get().strip()
        if not termino:
            return

        # Si hay exactamente una sugerencia, usarla
        if self.listbox_sugerencias.size() == 1:
            self.seleccionar_sugerencia()
        elif self.listbox_sugerencias.size() > 1:
            # Si hay múltiples, mostrar aviso
            messagebox.showinfo("Producto ambiguo", "Selecciona un producto de las sugerencias")

    def agregar_producto_desde_campo_texto(self, producto):
        """Agrega un producto al carrito desde el campo de búsqueda"""
        try:
            cantidad_deseada = int(self.entry_cantidad.get())
            if cantidad_deseada <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Error", "Cantidad inválida en el campo Qty")
            return

        if producto["stock"] <= 0:
            messagebox.showwarning("Sin stock", "Producto sin disponibilidad")
            return

        # Verificar si ya está en carrito
        for item in self.carrito:
            if item["id"] == producto["id"]:
                if item["cantidad"] + cantidad_deseada <= producto["stock"]:
                    item["cantidad"] += cantidad_deseada
                else:
                    messagebox.showwarning("Stock límite", "No hay suficientes unidades disponibles")
                self.actualizar_lista_venta()
                self.entry_producto.delete(0, "end")
                self.listbox_sugerencias.delete(0, "end")
                return

        # Si no existe en carrito
        if cantidad_deseada > producto["stock"]:
            messagebox.showwarning("Stock límite", "No hay suficientes unidades disponibles")
            return

        self.carrito.append({
            "id": producto["id"],
            "nombre": producto["nombre"],
            "precio": float(producto["precio"]),
            "cantidad": cantidad_deseada
        })

        self.actualizar_lista_venta()
        self.entry_producto.delete(0, "end")
        self.listbox_sugerencias.delete(0, "end")

    # =====================================================
    # MOTOR DE VENTA
    # =====================================================

    def actualizar_lista_venta(self):

        self.lista_venta.delete(0, "end")

        moneda = self.moneda_actual.get()
        total_base = 0

        for item in self.carrito:
            subtotal = item["precio"] * item["cantidad"]
            total_base += subtotal

            precio_convertido = convertir_moneda(subtotal, moneda)

            self.lista_venta.insert(
                "end",
                f'{item["nombre"]} x{item["cantidad"]} - {precio_convertido:.2f} {moneda}'
            )

        total_convertido = convertir_moneda(total_base, moneda)

        self.label_total.config(
            text=f"Total: {total_convertido:.2f} {moneda}"
        )


    def actualizar_total(self):
        self.actualizar_lista_venta()

    def eliminar_item_venta(self):
        """Quita el artículo seleccionado de la lista de venta y actualiza totales."""
        seleccionado = self.lista_venta.curselection()
        if not seleccionado:
            return
        idx = seleccionado[0]
        item = self.carrito[idx]
        confirmar = messagebox.askyesno("Confirmar", f"¿Eliminar {item['nombre']} de la venta?")
        if not confirmar:
            return
        self.carrito.pop(idx)
        self.actualizar_lista_venta()


    def finalizar_venta(self):

        if not self.carrito:
            messagebox.showwarning("Vacío", "No hay productos en la venta")
            return
        # Ventana de pagos que permite múltiples entradas y monedas
        ventana = tk.Toplevel(self)
        ventana.title("Método de Pago / Pagos")
        ventana.geometry("480x420")

        moneda = self.moneda_actual.get()
        total_base = sum(item["precio"] * item["cantidad"] for item in self.carrito)

        tk.Label(ventana, text=f"Total a pagar: {total_base:.2f} CUP", font=("Arial", 12, "bold")).pack(pady=8)

        frame_input = tk.Frame(ventana)
        frame_input.pack(pady=5)

        tk.Label(frame_input, text="Método:").grid(row=0, column=0)
        combo_metodo = ttk.Combobox(frame_input, values=["Efectivo", "Tarjeta", "Transferencia", "Otro"], state="readonly", width=12)
        combo_metodo.set("Efectivo")
        combo_metodo.grid(row=0, column=1, padx=5)

        tk.Label(frame_input, text="Moneda:").grid(row=0, column=2)
        combo_mon = ttk.Combobox(frame_input, values=obtener_monedas(), state="readonly", width=8)
        combo_mon.set(moneda)
        combo_mon.grid(row=0, column=3, padx=5)

        tk.Label(frame_input, text="Monto:").grid(row=1, column=0)
        entry_monto = tk.Entry(frame_input, width=12)
        entry_monto.grid(row=1, column=1, padx=5, pady=6)

        payments = []

        frame_payments = tk.Frame(ventana)
        frame_payments.pack(fill="both", expand=False, padx=10, pady=5)

        listp = tk.Listbox(frame_payments, height=8)
        listp.pack(fill="both", expand=True)

        def actualizar_resumen():
            # calcular total pagado en CUP
            total_pagado = 0.0
            for p in payments:
                total_pagado += p['monto_cup']

            restante = total_base - total_pagado
            mon_dest = combo_mostrar.get() if 'combo_mostrar' in globals() or 'combo_mostrar' in locals() else 'CUP'
            if restante > 0:
                convertido = convertir_moneda(restante, mon_dest)
                lbl_resumen.config(text=f"Pagado: {total_pagado:.2f} CUP — Falta: {restante:.2f} CUP ({convertido:.2f} {mon_dest})")
            else:
                cambio = -restante
                convertido = convertir_moneda(cambio, mon_dest)
                lbl_resumen.config(text=f"Pagado: {total_pagado:.2f} CUP — Cambio: {cambio:.2f} CUP ({convertido:.2f} {mon_dest})")

        def agregar_pago():
            try:
                monto = float(entry_monto.get())
            except Exception:
                messagebox.showerror("Error", "Monto inválido")
                return

            metodo_p = combo_metodo.get()
            moneda_p = combo_mon.get()

            monto_cup = convertir_a_cup(monto, moneda_p)

            payments.append({
                'metodo': metodo_p,
                'monto': monto,
                'moneda': moneda_p,
                'monto_cup': monto_cup
            })

            listp.insert('end', f"{metodo_p}: {monto:.2f} {moneda_p} ({monto_cup:.2f} CUP)")
            entry_monto.delete(0, 'end')
            actualizar_resumen()

        def eliminar_pago():
            sel = listp.curselection()
            if not sel:
                return
            idx = sel[0]
            listp.delete(idx)
            payments.pop(idx)
            actualizar_resumen()

        btn_frame = tk.Frame(ventana)
        btn_frame.pack(pady=6)

        tk.Button(btn_frame, text="Agregar pago", command=agregar_pago, bg="#007bff", fg="white").grid(row=0, column=0, padx=6)
        tk.Button(btn_frame, text="Eliminar pago", command=eliminar_pago, bg="#dc3545", fg="white").grid(row=0, column=1, padx=6)

        lbl_resumen = tk.Label(ventana, text="Pagado: 0.00 CUP — Falta: {0:.2f} CUP".format(total_base), font=("Arial", 11))
        lbl_resumen.pack(pady=6)

        # Selector para mostrar restante/cambio en otra moneda
        frame_mostrar = tk.Frame(ventana)
        frame_mostrar.pack(pady=4)
        tk.Label(frame_mostrar, text="Mostrar en:").pack(side="left")
        combo_mostrar = ttk.Combobox(frame_mostrar, values=obtener_monedas(), state="readonly", width=8)
        combo_mostrar.set('CUP')
        combo_mostrar.pack(side="left", padx=6)

        def confirmar():
            total_pagado = sum(p['monto_cup'] for p in payments)

            restante = total_base - total_pagado

            # Obtener moneda de visualización si existe
            try:
                mon_dest = combo_mostrar.get()
            except Exception:
                mon_dest = 'CUP'

            if restante > 0:
                convertido = convertir_moneda(restante, mon_dest)
                confirmar_reg = messagebox.askyesno("Monto insuficiente", f"Faltan {restante:.2f} CUP ({convertido:.2f} {mon_dest}). Registrar venta con deuda?")
                if not confirmar_reg:
                    return

            # Guardar venta
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_connection()
            cursor = conn.cursor()

            metodo_desc = 'Mixto' if len(payments) > 1 else (payments[0]['metodo'] if payments else combo_metodo.get())
            detalle_metodos = '; '.join([f"{p['metodo']} {p['monto']:.2f} {p['moneda']}" for p in payments]) or metodo_desc

            cursor.execute("""
                INSERT INTO ventas (fecha, total, moneda, metodo_pago, terminal_id)
                VALUES (?, ?, ?, ?, ?)
            """, (fecha, total_base, 'CUP', detalle_metodos, self.terminal_id))

            venta_id = cursor.lastrowid

            for item in self.carrito:
                subtotal = item["precio"] * item["cantidad"]
                cursor.execute("""
                    INSERT INTO detalle_venta (venta_id, producto_id, cantidad, subtotal)
                    VALUES (?, ?, ?, ?)
                """, (venta_id, item["id"], item["cantidad"], subtotal))

                cursor.execute("""
                    UPDATE productos
                    SET stock = stock - ?
                    WHERE id = ?
                """, (item["cantidad"], item["id"]))

            conn.commit()
            conn.close()

            # Registrar en caja (mantiene comportamiento previo)
            registrar_total_en_caja(total_base)

            # Guardar resumen de pagos en reportes
            resumen = f"Venta ID {venta_id} - Total {total_base:.2f} CUP - Pagos: {detalle_metodos} - Pagado(CUP): {total_pagado:.2f}"
            guardar_reporte('venta', resumen)

            # Limpiar carrito y UI
            self.carrito.clear()
            self.actualizar_lista_venta()
            self.cargar_productos()

            ventana.destroy()

            if restante > 0:
                convertido = convertir_moneda(restante, mon_dest)
                messagebox.showinfo("Venta registrada", f"Venta registrada con deuda de {restante:.2f} CUP ({convertido:.2f} {mon_dest})")
            else:
                cambio = -restante
                convertido = convertir_moneda(cambio, mon_dest)
                messagebox.showinfo("Venta Exitosa", f"Venta registrada correctamente. Cambio: {cambio:.2f} CUP ({convertido:.2f} {mon_dest})")

        btns_frame = tk.Frame(ventana)
        btns_frame.pack(pady=8)

        tk.Button(btns_frame, text="Confirmar Venta", bg="#28a745", fg="white", command=confirmar).pack(side="left", padx=6)
        tk.Button(btns_frame, text="Cancelar Venta", bg="#6c757d", fg="white", command=ventana.destroy).pack(side="left", padx=6)
    
    # =====================================================
    # GESTIÓN DE INVENTARIO (CRUD COMPLETO)
    # =====================================================

    def gestion_inventario(self):

        ventana = tk.Toplevel(self)
        ventana.title("Gestión de Inventario")
        ventana.geometry("900x550")

        # -------- TABLA --------
        tree = ttk.Treeview(
            ventana,
            columns=("ID", "Nombre", "Precio", "Stock", "StockMin"),
            show="headings"
        )

        for col in ("ID", "Nombre", "Precio", "Stock", "StockMin"):
            tree.heading(col, text=col)
            tree.column(col, width=120)

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # -------- CARGAR DATOS --------
        def cargar_tabla():
            for i in tree.get_children():
                tree.delete(i)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos")
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
            conn.close()

        cargar_tabla()

        # -------- FORMULARIO --------
        frame_form = tk.Frame(ventana)
        frame_form.pack(pady=10)

        labels = ["Nombre", "Precio", "Stock", "Stock Mínimo"]
        entries = {}

        for i, label in enumerate(labels):
            tk.Label(frame_form, text=label).grid(row=0, column=i)
            entry = tk.Entry(frame_form, width=15)
            entry.grid(row=1, column=i, padx=5)
            entries[label] = entry

        # -------- AGREGAR --------
        def agregar():
            try:
                nombre = entries["Nombre"].get()
                precio = float(entries["Precio"].get())
                stock = int(entries["Stock"].get())
                stock_min = int(entries["Stock Mínimo"].get())

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO productos (nombre, precio, stock, stock_minimo)
                    VALUES (?, ?, ?, ?)
                """, (nombre, precio, stock, stock_min))

                conn.commit()
                conn.close()

                cargar_tabla()
                self.cargar_productos()

                for e in entries.values():
                    e.delete(0, "end")

            except Exception as e:
                messagebox.showerror("Error", f"Datos inválidos\n{e}")

        # -------- EDITAR --------
        def editar():
            seleccionado = tree.focus()
            if not seleccionado:
                return

            try:
                valores = tree.item(seleccionado)["values"]
                producto_id = valores[0]

                nombre = entries["Nombre"].get()
                precio = float(entries["Precio"].get())
                stock = int(entries["Stock"].get())
                stock_min = int(entries["Stock Mínimo"].get())

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE productos
                    SET nombre=?, precio=?, stock=?, stock_minimo=?
                    WHERE id=?
                """, (nombre, precio, stock, stock_min, producto_id))

                conn.commit()
                conn.close()

                cargar_tabla()
                self.cargar_productos()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo editar\n{e}")

        # -------- ELIMINAR --------
        def eliminar():
            seleccionado = tree.focus()
            if not seleccionado:
                return

            valores = tree.item(seleccionado)["values"]
            producto_id = valores[0]

            confirmar = messagebox.askyesno("Confirmar", "¿Eliminar producto?")
            if not confirmar:
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id=?", (producto_id,))
            conn.commit()
            conn.close()

            cargar_tabla()
            self.cargar_productos()

        # -------- CARGAR EN FORM AL SELECCIONAR --------
        def seleccionar(event):
            seleccionado = tree.focus()
            if not seleccionado:
                return

            valores = tree.item(seleccionado)["values"]

            entries["Nombre"].delete(0, "end")
            entries["Precio"].delete(0, "end")
            entries["Stock"].delete(0, "end")
            entries["Stock Mínimo"].delete(0, "end")

            entries["Nombre"].insert(0, valores[1])
            entries["Precio"].insert(0, valores[2])
            entries["Stock"].insert(0, valores[3])
            entries["Stock Mínimo"].insert(0, valores[4])

        tree.bind("<<TreeviewSelect>>", seleccionar)

        # -------- BOTONES --------
        frame_btn = tk.Frame(ventana)
        frame_btn.pack(pady=10)

        tk.Button(frame_btn, text="Agregar", bg="#28a745", fg="white",
                  command=agregar).grid(row=0, column=0, padx=5)

        tk.Button(frame_btn, text="Editar", bg="#007bff", fg="white",
                  command=editar).grid(row=0, column=1, padx=5)

        tk.Button(frame_btn, text="Eliminar", bg="#dc3545", fg="white",
                  command=eliminar).grid(row=0, column=2, padx=5)
    # =====================================================
    # ADMINISTRACIÓN
    # =====================================================

    # -------- EDITAR TASAS --------
    def editar_tasas(self):

        ventana = tk.Toplevel(self)
        ventana.title("Editar Tasas de Moneda")
        ventana.geometry("450x350")

        tree = ttk.Treeview(
            ventana,
            columns=("Moneda", "Tasa"),
            show="headings"
        )

        tree.heading("Moneda", text="Moneda")
        tree.heading("Tasa", text="Tasa vs CUP")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def cargar():
            for i in tree.get_children():
                tree.delete(i)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, tasa FROM monedas")
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
            conn.close()

        cargar()

        frame = tk.Frame(ventana)
        frame.pack(pady=10)

        tk.Label(frame, text="Nueva Tasa:").pack(side="left")
        entry_tasa = tk.Entry(frame, width=10)
        entry_tasa.pack(side="left", padx=5)

        def actualizar():
            seleccionado = tree.focus()
            if not seleccionado:
                messagebox.showwarning("Seleccione", "Seleccione una moneda")
                return

            moneda = tree.item(seleccionado)["values"][0]

            try:
                nueva_tasa = float(entry_tasa.get())
            except:
                messagebox.showerror("Error", "Tasa inválida")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE monedas SET tasa=? WHERE nombre=?",
                (nueva_tasa, moneda)
            )
            conn.commit()
            conn.close()

            cargar()
            self.combo_moneda["values"] = obtener_monedas()
            entry_tasa.delete(0, "end")

        tk.Button(
            ventana,
            text="Actualizar",
            bg="#007bff",
            fg="white",
            command=actualizar
        ).pack(pady=5)

        # botón para eliminar la moneda seleccionada
        def eliminar_moneda():
            seleccionado = tree.focus()
            if not seleccionado:
                messagebox.showwarning("Seleccione", "Seleccione una moneda")
                return
            moneda = tree.item(seleccionado)["values"][0]
            if not messagebox.askyesno("Confirmar", f"¿Eliminar la moneda '{moneda}'?"):
                return
            if eliminar_moneda_db(moneda):
                cargar()
                self.combo_moneda["values"] = obtener_monedas()
            else:
                messagebox.showerror("Error", "No se puede eliminar esa moneda")

        tk.Button(
            ventana,
            text="Eliminar Moneda",
            bg="#dc3545",
            fg="white",
            command=eliminar_moneda
        ).pack(pady=5)

    def gestion_denominaciones(self):
        """Gestiona las denominaciones de billetes"""

        ventana = tk.Toplevel(self)
        ventana.title("Gestión de Denominaciones de Billetes")
        ventana.geometry("600x400")

        # Treeview para mostrar denominaciones
        tree = ttk.Treeview(
            ventana,
            columns=("Valor", "Nombre", "Activo"),
            show="headings",
            height=15
        )

        tree.heading("Valor", text="Valor (CUP)")
        tree.heading("Nombre", text="Nombre")
        tree.heading("Activo", text="Activo")
        
        tree.column("Valor", width=100)
        tree.column("Nombre", width=250)
        tree.column("Activo", width=100)
        
        # el widget Treeview no se empaqueta todavía; primero mostramos los controles de agregar/editar/eliminar

        def cargar_denominaciones():
            for i in tree.get_children():
                tree.delete(i)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, valor, nombre, activo FROM denominaciones_billetes ORDER BY valor DESC")
            for bid, valor, nombre, activo in cursor.fetchall():
                estado = "Sí" if activo else "No"
                tree.insert("", "end", iid=bid, values=(valor, nombre, estado))
            conn.close()

        cargar_denominaciones()

        frame_agregar = tk.LabelFrame(ventana, text="Agregar / Editar Denominación", font=("Arial", 10, "bold"))
        frame_agregar.pack(fill="x", padx=10, pady=10)

        frame_inputs = tk.Frame(frame_agregar)
        frame_inputs.pack(fill="x", padx=10, pady=10)

        tk.Label(frame_inputs, text="Valor:").pack(side="left", padx=5)
        entry_valor = tk.Entry(frame_inputs, width=10)
        entry_valor.pack(side="left", padx=5)

        tk.Label(frame_inputs, text="Nombre:").pack(side="left", padx=5)
        entry_nombre = tk.Entry(frame_inputs, width=30)
        entry_nombre.pack(side="left", padx=5)

        def agregar_denominacion():
            try:
                valor = float(entry_valor.get())
                nombre = entry_nombre.get().strip()
                if not nombre:
                    messagebox.showwarning("Validación", "Ingresa un nombre")
                    return
                if valor <= 0:
                    messagebox.showwarning("Validación", "El valor debe ser mayor a 0")
                    return
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO denominaciones_billetes (valor, nombre, activo) VALUES (?, ?, 1)",
                    (valor, nombre)
                )
                conn.commit()
                conn.close()

                cargar_denominaciones()
                entry_valor.delete(0, "end")
                entry_nombre.delete(0, "end")
                messagebox.showinfo("Éxito", "Denominación agregada")
            except ValueError:
                messagebox.showerror("Error", "Valor inválido")
            except Exception as e:
                if "UNIQUE" in str(e):
                    messagebox.showerror("Error", "Esta denominación ya existe")
                else:
                    messagebox.showerror("Error", str(e))

        tk.Button(frame_agregar, text="+ Agregar", command=agregar_denominacion, bg="#28a745", fg="white").pack(side="left", padx=10, pady=5)

        frame_acciones = tk.Frame(ventana)
        frame_acciones.pack(fill="x", padx=10, pady=10)

        def editar_denominacion():
            seleccionado = tree.focus()
            if not seleccionado:
                messagebox.showwarning("Seleccionar", "Selecciona una denominación")
                return

            bid = seleccionado
            valor, nombre, activo = tree.item(bid)["values"]

            ventana_edit = tk.Toplevel(ventana)
            ventana_edit.title("Editar Denominación")
            ventana_edit.geometry("400x150")

            tk.Label(ventana_edit, text="Valor:").pack(pady=5)
            entry_edit_valor = tk.Entry(ventana_edit, width=15)
            entry_edit_valor.insert(0, str(valor))
            entry_edit_valor.pack(pady=5)

            tk.Label(ventana_edit, text="Nombre:").pack(pady=5)
            entry_edit_nombre = tk.Entry(ventana_edit, width=30)
            entry_edit_nombre.insert(0, nombre)
            entry_edit_nombre.pack(pady=5)

            def guardar_cambios():
                try:
                    nuevo_valor = float(entry_edit_valor.get())
                    nuevo_nombre = entry_edit_nombre.get().strip()
                    if not nuevo_nombre:
                        messagebox.showwarning("Validación", "Ingresa un nombre")
                        return
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE denominaciones_billetes SET valor=?, nombre=? WHERE id=?",
                        (nuevo_valor, nuevo_nombre, bid)
                    )
                    conn.commit()
                    conn.close()

                    cargar_denominaciones()
                    ventana_edit.destroy()
                    messagebox.showinfo("Éxito", "Denominación actualizada")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            tk.Button(ventana_edit, text="Guardar", command=guardar_cambios, bg="#007bff", fg="white").pack(pady=10)

        def toggle_activo():
            seleccionado = tree.focus()
            if not seleccionado:
                messagebox.showwarning("Seleccionar", "Selecciona una denominación")
                return
            bid = seleccionado
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT activo FROM denominaciones_billetes WHERE id=?", (bid,))
            row = cursor.fetchone()
            if row:
                nuevo = 0 if row[0] else 1
                cursor.execute("UPDATE denominaciones_billetes SET activo=? WHERE id=?", (nuevo, bid))
                conn.commit()
            conn.close()
            cargar_denominaciones()

        def eliminar_denominacion_ui():
            seleccionado = tree.focus()
            if not seleccionado:
                messagebox.showwarning("Seleccionar", "Selecciona una denominación")
                return
            if not messagebox.askyesno("Confirmar", "¿Eliminar permanentemente esta denominación?"):
                return
            bid = seleccionado
            if eliminar_denominacion_db(bid):
                cargar_denominaciones()
                messagebox.showinfo("Éxito", "Denominación eliminada")
            else:
                messagebox.showerror("Error", "No se pudo eliminar la denominación")

        # botones de acción sobre la lista
        tk.Button(frame_acciones, text="✏️ Editar", command=editar_denominacion, bg="#007bff", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(frame_acciones, text="🗑️ Eliminar", command=eliminar_denominacion_ui, bg="#dc3545", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(frame_acciones, text="✓ Activar/Desactivar", command=toggle_activo, bg="#ffc107", fg="black", width=15).pack(side="left", padx=5)

        # empacamos la vista de árbol al final para que no ocupe todo el espacio
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        cargar_denominaciones()



    # -------- REPORTE DEL DÍA --------
    def reporte_dia(self):

        hoy = datetime.now().strftime("%Y-%m-%d")

        conn = get_connection()
        cursor = conn.cursor()

        # Detalle por producto (cantidad y subtotal) para las ventas del día
        cursor.execute("""
            SELECT p.nombre, SUM(d.cantidad) as cantidad, SUM(d.subtotal) as subtotal
            FROM detalle_venta d
            JOIN ventas v ON d.venta_id = v.id
            JOIN productos p ON d.producto_id = p.id
            WHERE v.fecha LIKE ?
            GROUP BY p.id, p.nombre
        """, (f"{hoy}%",))

        filas = cursor.fetchall()

        # Totales por método y total del día
        cursor.execute("SELECT SUM(total) FROM ventas WHERE fecha LIKE ?", (f"{hoy}%",))
        total_hoy = cursor.fetchone()[0] or 0.0

        efectivo = total_por_metodo("Efectivo")
        tarjeta = total_por_metodo("Tarjeta")
        transferencia = total_por_metodo("Transferencia")

        conn.close()

        detalle_lines = []
        for nombre, cantidad, subtotal in filas:
            detalle_lines.append(f"- {nombre}: {int(cantidad)} u. — {float(subtotal):.2f} CUP")

        detalle_text = "\n".join(detalle_lines) if detalle_lines else "No se registraron productos vendidos hoy."

        mensaje = "REPORTE DEL DÍA\n\n"
        mensaje += "Detalle de productos vendidos:\n"
        mensaje += detalle_text + "\n\n"
        mensaje += f"Total vendido: {total_hoy:.2f} CUP\n\n"
        mensaje += "Por método de pago:\n"
        mensaje += f"- Efectivo: {efectivo:.2f} CUP\n"
        mensaje += f"- Tarjeta: {tarjeta:.2f} CUP\n"
        mensaje += f"- Transferencia: {transferencia:.2f} CUP\n"

        # Guardar el reporte en histórico
        guardar_reporte("diario", mensaje)

        messagebox.showinfo("Reporte Diario", mensaje)

    # -------- GESTION DE USUARIOS Y PERMISOS --------
    def gestion_usuarios(self):
        ventana = tk.Toplevel(self)
        ventana.title("Gestión de Usuarios")
        ventana.geometry("900x500")

        frame_left = tk.Frame(ventana)
        frame_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(frame_left, columns=("ID", "Usuario", "Rol"), show="headings")
        tree.heading("ID", text="ID")
        tree.heading("Usuario", text="Usuario")
        tree.heading("Rol", text="Rol")
        tree.column("ID", width=40)
        tree.pack(fill="both", expand=True)

        def cargar_usuarios():
            for i in tree.get_children():
                tree.delete(i)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, rol FROM usuarios")
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
            conn.close()

        cargar_usuarios()

        # Panel derecho: formulario y permisos
        frame_right = tk.Frame(ventana)
        frame_right.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(frame_right, text="Usuario:").pack()
        entry_user = tk.Entry(frame_right)
        entry_user.pack()

        tk.Label(frame_right, text="Contraseña:").pack()
        entry_pass = tk.Entry(frame_right)
        entry_pass.pack()

        tk.Label(frame_right, text="Rol:").pack()
        entry_rol = tk.Entry(frame_right)
        entry_rol.pack()

        tk.Label(frame_right, text="Permisos:").pack(pady=(10,0))

        # cargar permisos disponibles
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, permiso, descripcion FROM permisos ORDER BY permiso")
        permisos = cursor.fetchall()
        conn.close()

        permiso_vars = {}
        for pid, perm, desc in permisos:
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(frame_right, text=f"{perm} - {desc}", variable=var)
            cb.pack(anchor="w")
            permiso_vars[pid] = var

        def seleccionar_usuario(event):
            sel = tree.focus()
            if not sel:
                return
            valores = tree.item(sel)["values"]
            uid = valores[0]
            entry_user.delete(0, 'end')
            entry_pass.delete(0, 'end')
            entry_rol.delete(0, 'end')
            entry_user.insert(0, valores[1])
            entry_rol.insert(0, valores[2])

            # cargar permisos asignados
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT permiso_id FROM usuario_permisos WHERE usuario_id=?", (uid,))
            asignados = {r[0] for r in cursor.fetchall()}
            conn.close()

            for pid, var in permiso_vars.items():
                var.set(1 if pid in asignados else 0)

        tree.bind("<<TreeviewSelect>>", seleccionar_usuario)

        def agregar_usuario():
            usuario = entry_user.get().strip()
            password = entry_pass.get().strip()
            rol = entry_rol.get().strip() or 'User'
            if not usuario or not password:
                messagebox.showerror("Error", "Usuario y contraseña requeridos")
                return
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", (usuario, password, rol))
                uid = cursor.lastrowid
                # asignar permisos seleccionados
                for pid, var in permiso_vars.items():
                    if var.get():
                        cursor.execute("INSERT INTO usuario_permisos (usuario_id, permiso_id) VALUES (?, ?)", (uid, pid))
                conn.commit()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear usuario\n{e}")
            finally:
                conn.close()
            cargar_usuarios()

        def editar_usuario():
            sel = tree.focus()
            if not sel:
                return
            valores = tree.item(sel)["values"]
            uid = valores[0]
            usuario = entry_user.get().strip()
            password = entry_pass.get().strip()
            rol = entry_rol.get().strip() or 'User'
            conn = get_connection()
            cursor = conn.cursor()
            try:
                if password:
                    cursor.execute("UPDATE usuarios SET username=?, password=?, rol=? WHERE id=?", (usuario, password, rol, uid))
                else:
                    cursor.execute("UPDATE usuarios SET username=?, rol=? WHERE id=?", (usuario, rol, uid))
                # actualizar permisos
                cursor.execute("DELETE FROM usuario_permisos WHERE usuario_id=?", (uid,))
                for pid, var in permiso_vars.items():
                    if var.get():
                        cursor.execute("INSERT INTO usuario_permisos (usuario_id, permiso_id) VALUES (?, ?)", (uid, pid))
                conn.commit()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo editar usuario\n{e}")
            finally:
                conn.close()
            cargar_usuarios()

        def eliminar_usuario():
            sel = tree.focus()
            if not sel:
                return
            valores = tree.item(sel)["values"]
            uid = valores[0]
            confirmar = messagebox.askyesno("Confirmar", "¿Eliminar usuario?")
            if not confirmar:
                return
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuario_permisos WHERE usuario_id=?", (uid,))
            cursor.execute("DELETE FROM usuarios WHERE id=?", (uid,))
            conn.commit()
            conn.close()
            cargar_usuarios()

        frame_btn = tk.Frame(frame_right)
        frame_btn.pack(pady=10)

        tk.Button(frame_btn, text="Agregar", bg="#28a745", fg="white", command=agregar_usuario).grid(row=0, column=0, padx=4)
        tk.Button(frame_btn, text="Editar", bg="#007bff", fg="white", command=editar_usuario).grid(row=0, column=1, padx=4)
        tk.Button(frame_btn, text="Eliminar", bg="#dc3545", fg="white", command=eliminar_usuario).grid(row=0, column=2, padx=4)

    # -------- CAMBIAR USUARIO --------
    def cambiar_usuario(self):
        ventana = tk.Toplevel(self)
        ventana.title("Cambiar Usuario")
        ventana.geometry("300x250")
        ventana.grab_set()

        tk.Label(ventana, text="Seleccione Usuario", font=("Arial", 12, "bold")).pack(pady=10)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM usuarios ORDER BY username")
        usuarios = cursor.fetchall()
        conn.close()

        usuario_map = {u[1]: u[0] for u in usuarios}
        usuario_list = [u[1] for u in usuarios]

        combo_usr = ttk.Combobox(ventana, values=usuario_list, state="readonly", width=25)
        combo_usr.pack(pady=10)

        tk.Label(ventana, text="Contraseña:").pack()
        entry_pass = tk.Entry(ventana, show="*", width=25)
        entry_pass.pack(pady=5)

        def autenticar():
            usuario = combo_usr.get()
            password = entry_pass.get()

            if not usuario or not password:
                messagebox.showerror("Error", "Usuario y contraseña requeridos")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rol FROM usuarios
                WHERE username=? AND password=?
            """, (usuario, password))
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                uid, rol = resultado
                self.usuario = usuario
                self.rol = rol
                ventana.destroy()
                messagebox.showinfo("Cambio de usuario", f"Sesión cambiada a: {usuario} ({rol})")
            else:
                messagebox.showerror("Error", "Credenciales incorrectas")

        tk.Button(ventana, text="Autenticar", bg="#007bff", fg="white", command=autenticar).pack(pady=15)

    # -------- CERRAR CAJA --------
    def cerrar_caja_ui(self):
        # Obtener datos de la caja abierta sin cerrarla todavía
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fondo_inicial, total_ventas
            FROM caja
            WHERE abierta = 1
            ORDER BY id DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()

        if not result:
            messagebox.showerror("Error", "No hay caja abierta")
            return

        caja_id, fondo_inicial, total_ventas = result
        total_esperado = float(fondo_inicial) + float(total_ventas)

        datos = {
            "caja_id": caja_id,
            "fondo_inicial": float(fondo_inicial),
            "total_ventas": float(total_ventas),
            "total_en_caja": total_esperado
        }

        # Abrir ventana de balance de caja (sin cerrar aún)
        self.ventana_balance_caja(datos)

    def ventana_balance_caja(self, datos_caja):
        """Ventana modal para hacer balance de billetes en cierre de caja"""
        
        ventana = tk.Toplevel(self)
        ventana.title("Balance de Caja")
        # ajustar altura mayor y permitir redimensionar para asegurar que los botones sean visibles
        ventana.geometry("500x550")
        ventana.resizable(True, True)

        # Total esperado
        total_esperado = datos_caja['total_en_caja']

        # Frame superior con información
        frame_info = tk.Frame(ventana, bg="#e9ecef")
        frame_info.pack(fill="x", padx=10, pady=10)

        tk.Label(
            frame_info,
            text="BALANCE DE CIERRE DE CAJA",
            font=("Arial", 14, "bold"),
            bg="#e9ecef"
        ).pack()

        tk.Label(
            frame_info,
            text=f"Total esperado: {total_esperado:.2f} CUP",
            font=("Arial", 12),
            bg="#e9ecef"
        ).pack()

        # Frame para denominaciones
        frame_denominaciones = tk.Frame(ventana)
        frame_denominaciones.pack(fill="both", expand=True, padx=10, pady=10)

        # Obtener denominaciones de la BD
        denominaciones = obtener_denominaciones_billetes()
        
        # Variables para almacenar cantidades
        vars_billetes = {}

        if not denominaciones:
            tk.Label(frame_denominaciones,
                     text="No hay denominaciones configuradas. Agrega algunas desde Administración → Denominaciones.",
                     font=("Arial", 11), fg="red").pack(pady=20)
        else:
            tk.Label(frame_denominaciones, text="Billetes:", font=("Arial", 11, "bold")).pack(anchor="w")

        frame_billetes = tk.Frame(frame_denominaciones)
        frame_billetes.pack(fill="x", padx=10, pady=5)

        for bid, valor, nombre in denominaciones:
            frame_row = tk.Frame(frame_billetes)
            frame_row.pack(fill="x", pady=3)

            tk.Label(frame_row, text=f"{nombre}:", width=15).pack(side="left")
            
            var_cantidad = tk.IntVar(value=0)
            vars_billetes[valor] = var_cantidad

            spinbox = tk.Spinbox(
                frame_row,
                from_=0,
                to=1000,
                textvariable=var_cantidad,
                width=8
            )
            spinbox.pack(side="left", padx=5)

            tk.Label(frame_row, text="unidades", width=15).pack(side="left")

        # Frame para total calculado
        frame_total = tk.Frame(ventana, bg="#f0f0f0")
        frame_total.pack(fill="x", padx=10, pady=10)

        label_total_fisico = tk.Label(
            frame_total,
            text="Total físico: 0.00 CUP",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0"
        )
        label_total_fisico.pack()

        label_diferencia = tk.Label(
            frame_total,
            text="Diferencia: 0.00 CUP",
            font=("Arial", 12),
            bg="#f0f0f0"
        )
        label_diferencia.pack()

        def calcular_total(*args):
            """Calcula el total físico y la diferencia"""
            total_fisico = 0
            for bid, valor, nombre in denominaciones:
                try:
                    cantidad = int(vars_billetes[valor].get())
                except Exception:
                    try:
                        cantidad = int(float(vars_billetes[valor].get()))
                    except Exception:
                        cantidad = 0
                total_fisico += cantidad * valor
            diferencia = total_fisico - total_esperado

            label_total_fisico.config(text=f"Total físico: {total_fisico:.2f} CUP")
            
            color = "#28a745" if diferencia == 0 else "#ff9800" if diferencia > 0 else "#dc3545"
            label_diferencia.config(
                text=f"Diferencia: {diferencia:+.2f} CUP",
                fg="white",
                bg=color
            )

        # Bind para actualizar totales
        for var in vars_billetes.values():
            try:
                var.trace_add("write", lambda *a: calcular_total())
            except Exception:
                var.trace("w", calcular_total)

        # Frame de botones
        frame_botones = tk.Frame(ventana)
        frame_botones.pack(fill="x", padx=10, pady=10)

        def guardar_balance(cerrar=False):
            """Guarda el balance en la BD. Si cerrar=True también cierra la caja."""
            total_fisico = sum(
                vars_billetes[valor].get() * valor
                for bid, valor, nombre in denominaciones
            )

            caja_id = datos_caja.get("caja_id")

            conn = get_connection()
            cursor = conn.cursor()

            # Guardar cada denominación
            for bid, valor, nombre in denominaciones:
                cantidad = vars_billetes[valor].get()
                if cantidad > 0:
                    subtotal = cantidad * valor
                    cursor.execute(
                        "INSERT INTO balance_caja (caja_id, denominacion, cantidad, subtotal) VALUES (?, ?, ?, ?)",
                        (caja_id, valor, cantidad, subtotal)
                    )

            if cerrar:
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "UPDATE caja SET fecha_cierre = ?, abierta = 0 WHERE id = ?",
                    (fecha_cierre, caja_id)
                )

            conn.commit()
            conn.close()

            diferencia = total_fisico - total_esperado

            mensaje = f"""
BALANCE COMPLETADO

Fondo inicial: {datos_caja['fondo_inicial']:.2f} CUP
Total ventas: {datos_caja['total_ventas']:.2f} CUP
----------------------------------
Total esperado: {total_esperado:.2f} CUP
Total físico: {total_fisico:.2f} CUP
----------------------------------
Diferencia: {diferencia:+.2f} CUP
"""
            # Mostrar mensaje informativo
            messagebox.showinfo("Balance Guardado", mensaje)

            if cerrar:
                # Confirmar cierre exitoso
                messagebox.showinfo("Cierre de Caja", "Cierre de caja exitoso")
                ventana.destroy()
                # Abrir nueva apertura de caja
                self.ventana_apertura_caja()

        tk.Button(
            frame_botones,
            text="Guardar Balance",
            command=guardar_balance,
            bg="#28a745",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5)
        def confirmar_cierre():
            if not messagebox.askyesno("Confirmar Cierre", "¿Estás seguro que deseas cerrar la caja? Esta acción guardará el balance y cerrará la caja."):
                return

            # Desactivar entradas para evitar doble envío
            try:
                for row in frame_billetes.winfo_children():
                    for w in row.winfo_children():
                        try:
                            if isinstance(w, tk.Spinbox):
                                w.config(state='disabled')
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                for w in frame_botones.winfo_children():
                    try:
                        w.config(state='disabled')
                    except Exception:
                        pass
            except Exception:
                pass

            guardar_balance(cerrar=True)

        tk.Button(
            frame_botones,
            text="Confirmar Cierre",
            command=confirmar_cierre,
            bg="#0056b3",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5, pady=5)

        tk.Button(
            frame_botones,
            text="Cancelar",
            command=ventana.destroy,
            bg="#6c757d",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5, pady=5)

    def balance_caja_manual(self):
        """Permite hacer balance de caja sin cerrarla"""
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fondo_inicial, total_ventas
            FROM caja
            WHERE abierta = 1
            ORDER BY id DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            messagebox.showerror("Error", "No hay caja abierta")
            return
        
        caja_id, fondo_inicial, total_ventas = result
        total_esperado = float(fondo_inicial) + float(total_ventas)
        
        # Preparar datos en formato esperado
        datos_caja = {
            "caja_id": caja_id,
            "fondo_inicial": float(fondo_inicial),
            "total_ventas": float(total_ventas),
            "total_en_caja": total_esperado
        }
        
        # Abrir ventana de balance sin cerrar caja (pero permitirá cerrar si se desea)
        self.ventana_balance_caja_manual(datos_caja)

    def ventana_balance_caja_manual(self, datos_caja):
        """Ventana modal para hacer balance de billetes sin cerrar caja"""
        
        ventana = tk.Toplevel(self)
        ventana.title("Balance de Caja (sin cerrar)")
        # altura incrementada y ventana redimensionable
        ventana.geometry("500x550")
        ventana.resizable(True, True)

        # Total esperado
        total_esperado = datos_caja['total_en_caja']

        # Frame superior con información
        frame_info = tk.Frame(ventana, bg="#e9ecef")
        frame_info.pack(fill="x", padx=10, pady=10)

        tk.Label(
            frame_info,
            text="BALANCE DE CAJA (SIN CERRAR)",
            font=("Arial", 14, "bold"),
            bg="#e9ecef"
        ).pack()

        tk.Label(
            frame_info,
            text=f"Total esperado: {total_esperado:.2f} CUP",
            font=("Arial", 12),
            bg="#e9ecef"
        ).pack()

        # Frame para denominaciones
        frame_denominaciones = tk.Frame(ventana)
        frame_denominaciones.pack(fill="both", expand=True, padx=10, pady=10)

        # Obtener denominaciones de la BD
        denominaciones = obtener_denominaciones_billetes()
        
        # Variables para almacenar cantidades
        vars_billetes = {}

        if not denominaciones:
            tk.Label(frame_denominaciones,
                     text="No hay denominaciones configuradas. Agrega algunas desde Administración → Denominaciones.",
                     font=("Arial", 11), fg="red").pack(pady=20)
        else:
            tk.Label(frame_denominaciones, text="Billetes:", font=("Arial", 11, "bold")).pack(anchor="w")

        frame_billetes = tk.Frame(frame_denominaciones)
        frame_billetes.pack(fill="x", padx=10, pady=5)

        for bid, valor, nombre in denominaciones:
            frame_row = tk.Frame(frame_billetes)
            frame_row.pack(fill="x", pady=3)

            tk.Label(frame_row, text=f"{nombre}:", width=15).pack(side="left")
            
            var_cantidad = tk.IntVar(value=0)
            vars_billetes[valor] = var_cantidad

            spinbox = tk.Spinbox(
                frame_row,
                from_=0,
                to=1000,
                textvariable=var_cantidad,
                width=8
            )
            spinbox.pack(side="left", padx=5)

            tk.Label(frame_row, text="unidades", width=15).pack(side="left")

        # Frame para total calculado
        frame_total = tk.Frame(ventana, bg="#f0f0f0")
        frame_total.pack(fill="x", padx=10, pady=10)

        label_total_fisico = tk.Label(
            frame_total,
            text="Total físico: 0.00 CUP",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0"
        )
        label_total_fisico.pack()

        label_diferencia = tk.Label(
            frame_total,
            text="Diferencia: 0.00 CUP",
            font=("Arial", 12),
            bg="#f0f0f0"
        )
        label_diferencia.pack()

        def calcular_total(*args):
            """Calcula el total físico y la diferencia"""
            total_fisico = 0
            for bid, valor, nombre in denominaciones:
                try:
                    cantidad = int(vars_billetes[valor].get())
                except Exception:
                    try:
                        cantidad = int(float(vars_billetes[valor].get()))
                    except Exception:
                        cantidad = 0
                total_fisico += cantidad * valor
            diferencia = total_fisico - total_esperado

            label_total_fisico.config(text=f"Total físico: {total_fisico:.2f} CUP")
            
            color = "#28a745" if diferencia == 0 else "#ff9800" if diferencia > 0 else "#dc3545"
            label_diferencia.config(
                text=f"Diferencia: {diferencia:+.2f} CUP",
                fg="white",
                bg=color
            )

        # Bind para actualizar totales
        for var in vars_billetes.values():
            try:
                var.trace_add("write", lambda *a: calcular_total())
            except Exception:
                var.trace("w", calcular_total)

        # Frame de botones
        frame_botones = tk.Frame(ventana)
        frame_botones.pack(fill="x", padx=10, pady=10)

        def guardar_balance(cerrar=False):
            """Guarda el balance en la BD. Si cerrar=True también cierra la caja."""
            total_fisico = sum(
                vars_billetes[valor].get() * valor
                for bid, valor, nombre in denominaciones
            )

            caja_id = datos_caja.get("caja_id")

            conn = get_connection()
            cursor = conn.cursor()

            # Guardar cada denominación
            for bid, valor, nombre in denominaciones:
                cantidad = vars_billetes[valor].get()
                if cantidad > 0:
                    subtotal = cantidad * valor
                    cursor.execute(
                        "INSERT INTO balance_caja (caja_id, denominacion, cantidad, subtotal) VALUES (?, ?, ?, ?)",
                        (caja_id, valor, cantidad, subtotal)
                    )

            if cerrar and caja_id is not None:
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "UPDATE caja SET fecha_cierre = ?, abierta = 0 WHERE id = ?",
                    (fecha_cierre, caja_id)
                )

            conn.commit()
            conn.close()

            diferencia = total_fisico - total_esperado

            mensaje = f"""
BALANCE COMPLETADO

Fondo inicial: {datos_caja['fondo_inicial']:.2f} CUP
Total ventas: {datos_caja['total_ventas']:.2f} CUP
----------------------------------
Total esperado: {total_esperado:.2f} CUP
Total físico: {total_fisico:.2f} CUP
----------------------------------
Diferencia: {diferencia:+.2f} CUP
"""
            messagebox.showinfo("Balance Guardado", mensaje)

            if cerrar:
                messagebox.showinfo("Cierre de Caja", "Cierre de caja exitoso")
                ventana.destroy()
                self.ventana_apertura_caja()

        tk.Button(
            frame_botones,
            text="Guardar Balance",
            command=guardar_balance,
            bg="#28a745",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5)

        def confirmar_cierre():
            if not messagebox.askyesno("Confirmar Cierre", "¿Estás seguro que deseas cerrar la caja? Esta acción guardará el balance y cerrará la caja."):
                return
            try:
                for row in frame_billetes.winfo_children():
                    for w in row.winfo_children():
                        try:
                            if isinstance(w, tk.Spinbox):
                                w.config(state='disabled')
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                for w in frame_botones.winfo_children():
                    try:
                        w.config(state='disabled')
                    except Exception:
                        pass
            except Exception:
                pass
            guardar_balance(cerrar=True)

        tk.Button(
            frame_botones,
            text="Confirmar Cierre",
            command=confirmar_cierre,
            bg="#0056b3",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5, pady=5)

        tk.Button(
            frame_botones,
            text="Cancelar",
            command=ventana.destroy,
            bg="#6c757d",
            fg="white",
            font=("Arial", 11)
        ).pack(fill="x", padx=5, pady=5)

    # -------- HISTÓRICO DE REPORTES --------
    def mostrar_historico_reportes(self):
        ventana = tk.Toplevel(self)
        ventana.title("Histórico de Reportes")
        ventana.geometry("700x500")

        frame_top = tk.Frame(ventana)
        frame_top.pack(fill="both", expand=True, padx=10, pady=10)

        listbox = tk.Listbox(frame_top, width=60)
        listbox.pack(side="left", fill="y")

        text = tk.Text(frame_top)
        text.pack(side="right", fill="both", expand=True)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, tipo FROM reportes ORDER BY id DESC")
        filas = cursor.fetchall()
        conn.close()

        id_map = {}
        for idx, (rid, fecha, tipo) in enumerate(filas):
            display = f"{fecha} — {tipo}"
            listbox.insert("end", display)
            id_map[idx] = rid

        def on_select(evt):
            sel = listbox.curselection()
            if not sel:
                return
            rid = id_map[sel[0]]
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT contenido FROM reportes WHERE id=?", (rid,))
            row = cursor.fetchone()
            conn.close()

            text.delete("1.0", "end")
            if row:
                text.insert("1.0", row[0])

        listbox.bind("<<ListboxSelect>>", on_select)

    def mostrar_notificaciones_stock_critico(self):
        """Muestra notificaciones de productos con stock crítico"""
        productos_criticos = obtener_productos_stock_critico()
        
        if productos_criticos:
            mensaje = "ALERTA: Productos con Stock Crítico:\n\n"
            for pid, nombre, stock, stock_min in productos_criticos:
                mensaje += f"• {nombre}: {stock} unidades (mínimo: {stock_min})\n"
            
            messagebox.showwarning("Stock Crítico", mensaje)

    def mostrar_dashboard(self):
        """Muestra un dashboard con estadísticas"""
        
        ventana = tk.Toplevel(self)
        ventana.title("Dashboard de Ventas")
        ventana.geometry("900x700")

        # Frame superior con estadísticas del día
        frame_hoy = tk.LabelFrame(ventana, text="Hoy", font=("Arial", 12, "bold"))
        frame_hoy.pack(fill="x", padx=10, pady=10)

        stats_hoy = obtener_estadisticas_hoy()
        
        # Crear grid con stats
        frame_grid = tk.Frame(frame_hoy)
        frame_grid.pack(fill="x", padx=10, pady=10)

        # Total de ventas
        tk.Label(frame_grid, text="Total Ventas:", font=("Arial", 10, "bold")).pack(side="left", padx=10)
        tk.Label(frame_grid, text=f"${stats_hoy['total_ventas']:.2f} CUP", font=("Arial", 11), fg="#28a745").pack(side="left", padx=10)

        # Número de transacciones
        tk.Label(frame_grid, text="Transacciones:", font=("Arial", 10, "bold")).pack(side="left", padx=10)
        tk.Label(frame_grid, text=str(stats_hoy['num_transacciones']), font=("Arial", 11), fg="#007bff").pack(side="left", padx=10)

        # Producto más vendido
        if stats_hoy['mas_vendido']:
            tk.Label(frame_grid, text="Más Vendido:", font=("Arial", 10, "bold")).pack(side="left", padx=10)
            tk.Label(frame_grid, text=f"{stats_hoy['mas_vendido'][0]} (x{stats_hoy['mas_vendido'][1]})", font=("Arial", 11), fg="#ff9800").pack(side="left", padx=10)

        # Frame de métodos de pago
        frame_metodos = tk.LabelFrame(ventana, text="Métodos de Pago", font=("Arial", 12, "bold"))
        frame_metodos.pack(fill="x", padx=10, pady=10)

        if stats_hoy['metodos_pago']:
            for metodo, cantidad, monto in stats_hoy['metodos_pago']:
                frame_m = tk.Frame(frame_metodos)
                frame_m.pack(fill="x", padx=10, pady=5)
                
                tk.Label(frame_m, text=f"{metodo}", font=("Arial", 10, "bold"), width=20).pack(side="left")
                tk.Label(frame_m, text=f"${monto:.2f} CUP", font=("Arial", 10)).pack(side="left", padx=50)
                tk.Label(frame_m, text=f"({cantidad} trans.)", font=("Arial", 9), fg="#666").pack(side="left")
        else:
            tk.Label(frame_metodos, text="Sin ventas hoy", font=("Arial", 10), fg="#999").pack(pady=10)

        # Frame de últimos 7 días
        frame_periodo = tk.LabelFrame(ventana, text="Últimos 7 Días", font=("Arial", 12, "bold"))
        frame_periodo.pack(fill="both", expand=True, padx=10, pady=10)

        datos_periodo = obtener_estadisticas_periodo(7)

        if datos_periodo:
            # Crear tabla simple
            tree_frame = tk.Frame(frame_periodo)
            tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

            tree = ttk.Treeview(tree_frame, columns=("Fecha", "Total"), show="headings", height=10)
            tree.heading("Fecha", text="Fecha")
            tree.heading("Total", text="Total (CUP)")
            
            tree.column("Fecha", width=100)
            tree.column("Total", width=100)
            
            total_periodo = 0
            for fecha, total_dia in datos_periodo:
                tree.insert("", "end", values=(fecha, f"${total_dia:.2f}"))
                total_periodo += total_dia
            
            tree.pack(fill="both", expand=True)

            # Total del período
            frame_total_periodo = tk.Frame(frame_periodo)
            frame_total_periodo.pack(fill="x", padx=10, pady=10)
            
            tk.Label(frame_total_periodo, text="Total 7 días:", font=("Arial", 11, "bold")).pack(side="left")
            tk.Label(frame_total_periodo, text=f"${total_periodo:.2f} CUP", font=("Arial", 11, "bold"), fg="#28a745").pack(side="left", padx=10)

        # Frame de información general
        frame_info = tk.Frame(ventana)
        frame_info.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_info, text=f"Terminal: {self.terminal_id}", font=("Arial", 9), fg="#666").pack(anchor="w")
        tk.Label(frame_info, text=f"Usuario: {self.usuario}", font=("Arial", 9), fg="#666").pack(anchor="w")
        tk.Label(frame_info, text=f"Actualizado: {datetime.now().strftime('%H:%M:%S')}", font=("Arial", 9), fg="#666").pack(anchor="w")

    # -------- VENTANA APERTURA CAJA --------
    def ventana_apertura_caja(self):

        ventana = tk.Toplevel(self)
        ventana.title("Abrir Caja")
        ventana.geometry("300x200")
        ventana.grab_set()

        tk.Label(
            ventana,
            text="Fondo Inicial",
            font=("Arial", 12, "bold")
        ).pack(pady=10)

        entry = tk.Entry(ventana)
        entry.pack(pady=5)

        def abrir():
            try:
                fondo = float(entry.get())
            except:
                messagebox.showerror("Error", "Monto inválido")
                return

            abrir_caja(fondo)
            ventana.destroy()

        tk.Button(
            ventana,
            text="Abrir Caja",
            bg="#28a745",
            fg="white",
            command=abrir
        ).pack(pady=10)
# =====================================================
# LOGIN
# =====================================================

class Login(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Login - POS Profesional")
        self.geometry("350x280")
        self.configure(bg="#f4f6f9")

        tk.Label(self, text="POS Profesional",
                 font=("Arial", 16, "bold"),
                 bg="#f4f6f9").pack(pady=20)

        tk.Label(self, text="Usuario", bg="#f4f6f9").pack()
        
        # Cargar lista de usuarios
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM usuarios ORDER BY username")
        usuarios = [u[0] for u in cursor.fetchall()]
        conn.close()
        
        self.combo_user = ttk.Combobox(self, values=usuarios, state="readonly", width=25)
        self.combo_user.pack(pady=5)
        if usuarios:
            self.combo_user.set(usuarios[0])

        tk.Label(self, text="Contraseña", bg="#f4f6f9").pack(pady=(10,0))
        self.entry_pass = tk.Entry(self, show="*", width=25)
        self.entry_pass.pack(pady=5)

        tk.Button(self, text="Ingresar",
                  bg="#007bff", fg="white",
                  command=self.validar).pack(pady=15)

    def validar(self):

        user = self.combo_user.get()
        password = self.entry_pass.get()

        if not user or not password:
            messagebox.showerror("Error", "Usuario y contraseña requeridos")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rol FROM usuarios
            WHERE username=? AND password=?
        """, (user, password))

        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            rol = resultado[0]
            self.destroy()
            app = POS(usuario=user, rol=rol)
            app.mainloop()
        else:
            messagebox.showerror("Error", "Credenciales incorrectas")
        
# =====================================================
# EJECUCIÓN PRINCIPAL CON LOGIN
# =====================================================

if __name__ == "__main__":

    inicializar_db()

    login = Login()
    login.mainloop()

