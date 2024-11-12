from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = "secretkey"
# Configuración de la base de datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'biblioteca_escolar'

mysql = MySQL(app)

#Ruta Home
@app.route('/')
def home():
    return render_template('home.html')

# Ruta para login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE username = %s AND password = %s', (username, password))
        usuario = cursor.fetchone()
        if usuario:
            session['loggedin'] = True
            session['usuario_id'] = usuario['id']
            session['username'] = usuario['username']
            session['tipo_usuario'] = usuario['tipo_usuario']
            session['nombre'] = usuario['nombre']
            return redirect('/index')
        else:
            return "Usuario o contraseña incorrectos"
    return render_template('login.html')

# Ruta para el index
@app.route('/index')
def index():
    if 'loggedin' in session:
        if session['tipo_usuario'] == 'administrador':
            return render_template('index_admin.html')
        else:
            return render_template('index_user.html')
    return redirect('/login')

# Ruta para logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('usuario_id', None)
    session.pop('username', None)
    session.pop('tipo_usuario', None)
    return redirect('/login')

# Ruta para registrar nuevos usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        apellidos = request.form['apellidos']
        nombre = request.form['nombre']
        tipo_usuario = 'alumno'  # Forzamos que el tipo de usuario siempre sea "alumno"

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO usuarios (username, password, nombre, apellidos, tipo_usuario) VALUES (%s, %s, %s, %s, %s)', 
                       (username, password, nombre, apellidos, tipo_usuario))
        mysql.connection.commit()
        cursor.close()

        return redirect('/login')
    return render_template('register.html')

# Rutas para libros disponibles
@app.route('/libros_disponibles')
def libros_disponibles():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM libros')
        libros = cursor.fetchall()
        cursor.close()

        # Verifica si los libros se están obteniendo correctamente
        if not libros:
            print("No se encontraron libros.")
        else:
            print("Libros obtenidos: ", libros)

        return render_template('libros_disponibles.html', libros=libros)
    return redirect('/login')

# Ruta para que los usuarios (alumnos) vean los libros disponibles
@app.route('/libros_disponibles_usuario')
def libros_disponibles_usuario():
    if 'loggedin' in session and session['tipo_usuario'] == 'alumno':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Cambiar a DictCursor
        cursor.execute("SELECT * FROM libros")
        libros = cursor.fetchall()
        
        # Verificación en la consola
        print(f"Libros obtenidos: {libros}")  # Verificar en la consola si se obtienen libros
        
        cursor.close()
        if libros:
            return render_template('libros_disponibles.html', libros=libros)
        else:
            return render_template('libros_disponibles.html', libros=[], mensaje="No hay libros disponibles.")
    else:
        print(f"Sesión inválida o no es un alumno: {session}")
    return redirect('/login')

# Ruta para registrar libros (solo administrador)
@app.route('/registrar_libro', methods=['GET', 'POST'])
def registrar_libro():
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        if request.method == 'POST':
            titulo = request.form['titulo']
            autor = request.form['autor']
            genero = request.form['genero']
            año_publicacion = request.form['año_publicacion']
            ejemplares = request.form['ejemplares']
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO libros (titulo, autor, genero, año_publicacion, ejemplares) VALUES (%s, %s, %s, %s, %s)', 
                           (titulo, autor, genero, año_publicacion, ejemplares))
            mysql.connection.commit()
            cursor.close()
            return redirect('/libros_disponibles')
        return render_template('registrar_libro.html')
    return redirect('/login')

# Ruta para eliminar un libro
@app.route('/eliminar_libro/<int:libro_id>', methods=['POST'])
def eliminar_libro(libro_id):
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM libros WHERE id = %s", (libro_id,))
        mysql.connection.commit()
        cursor.close()
        return redirect('/libros_disponibles')
    return redirect('/login')

# Ruta para editar el stock de un libro
@app.route('/editar_libro/<int:libro_id>', methods=['GET', 'POST'])
def editar_libro(libro_id):
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM libros WHERE id = %s", (libro_id,))
        libro = cursor.fetchone()
        cursor.close()

        if not libro:
            return "Libro no encontrado", 404

        if request.method == 'POST':
            ejemplares = request.form['ejemplares']

            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE libros SET ejemplares = %s WHERE id = %s", (ejemplares, libro_id))
            mysql.connection.commit()
            cursor.close()

            return redirect('/libros_disponibles')

        return render_template('editar_libro.html', libro=libro)
    return redirect('/login')

# Ruta para el formulario y prestar un libro
@app.route('/prestamo_libro/<int:libro_id>', methods=['GET', 'POST'])
def prestamo_libro(libro_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Cambiar a DictCursor
        cursor.execute("SELECT * FROM libros WHERE id = %s", (libro_id,))
        libro = cursor.fetchone()
        cursor.close()

        if not libro:
            return "Libro no encontrado", 404

        if request.method == 'POST':
            solicitante = request.form['solicitante']
            fecha_prestamo = request.form['fecha_prestamo']
            fecha_entrega = request.form['fecha_entrega']

            if not solicitante or not fecha_prestamo or not fecha_entrega:
                return "Todos los campos son requeridos", 400

            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO prestamos (libro_id, solicitante, fecha_prestamo, fecha_entrega) 
                VALUES (%s, %s, %s, %s)
            """, (libro_id, solicitante, fecha_prestamo, fecha_entrega))

            cursor.execute("UPDATE libros SET ejemplares = ejemplares - 1 WHERE id = %s", (libro_id,))
            mysql.connection.commit()
            cursor.close()

            return redirect('/libros_disponibles')

        # Imprimir los detalles del libro para depuración
        print(libro)

        return render_template('prestamo_libro.html', libro=libro)
    return redirect('/login')

# Ruta para ver los libros prestados
@app.route('/libros_prestados')
def libros_prestados():
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT prestamos.id, prestamos.solicitante, prestamos.fecha_prestamo, prestamos.fecha_entrega, prestamos.libro_id, libros.titulo 
            FROM prestamos 
            JOIN libros ON prestamos.libro_id = libros.id 
            WHERE prestamos.devuelto = 0
        """)
        prestamos = cursor.fetchall()
        cursor.close()
        return render_template('libros_prestados.html', prestamos=prestamos)
    return redirect('/login')

# Ruta para marcar un libro como devuelto
@app.route('/devolver_libro/<int:prestamo_id>', methods=['POST'])
def devolver_libro(prestamo_id):
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE prestamos SET devuelto = 1 WHERE id = %s", (prestamo_id,))
        cursor.execute("UPDATE libros SET ejemplares = ejemplares + 1 WHERE id = (SELECT libro_id FROM prestamos WHERE id = %s)", (prestamo_id,))
        mysql.connection.commit()
        cursor.close()
        return redirect('/libros_prestados')
    return redirect('/login')

# Ruta historial prestamos
@app.route('/reporte_prestamos')
def reporte_prestamos():
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT prestamos.id, prestamos.solicitante, prestamos.fecha_prestamo, prestamos.fecha_entrega, prestamos.libro_id, libros.titulo 
            FROM prestamos 
            JOIN libros ON prestamos.libro_id = libros.id 
            WHERE prestamos.devuelto = 1
        """)
        prestamos_finalizados = cursor.fetchall()
        cursor.close()
        return render_template('reporte_prestamos.html', prestamos=prestamos_finalizados)
    return redirect('/login')

# Ruta para eliminar un préstamo
@app.route('/eliminar_prestamo/<int:prestamo_id>', methods=['POST'])
def eliminar_prestamo(prestamo_id):
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM prestamos WHERE id = %s", (prestamo_id,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('reporte_prestamos'))
    return redirect('/login')

# Ruta para ver los usuarios registrados (solo para administradores)
@app.route('/ver_usuarios')
def ver_usuarios():
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, username, nombre, apellidos, tipo_usuario FROM usuarios")
        usuarios = cursor.fetchall()
        cursor.close()
        return render_template('ver_usuarios.html', usuarios=usuarios)
    return redirect('/login')
# Ruta para eliminar un usuario (solo para administradores)
@app.route('/eliminar_usuario/<int:usuario_id>', methods=['POST'])
def eliminar_usuario(usuario_id):
    if 'loggedin' in session and session['tipo_usuario'] == 'administrador':
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('ver_usuarios'))
    return redirect('/login')



# Abrir el navegador automáticamente al iniciar la app
def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    threading.Timer(1, abrir_navegador).start()  # Abrir el navegador después de 1 segundo
    app.run(debug=True)
