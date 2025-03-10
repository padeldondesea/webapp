from flask import Flask, render_template, request, redirect, jsonify
import json
import random
import itertools

app = Flask(__name__)

PASSWORD_ADMIN = "P@d3!"

def cargar_datos():
    try:
        with open('jugadores.json', 'r') as f:
            data = json.load(f)
            if "n_canchas" not in data["torneo"]:
                data["torneo"]["n_canchas"] = 0
            if "n_bloques" not in data["torneo"]:
                data["torneo"]["n_bloques"] = 0
            if "espera" not in data["torneo"]:
                data["torneo"]["espera"] = []
            if "resultados" not in data["torneo"]:
                data["torneo"]["resultados"] = {}
            return data
    except FileNotFoundError:
        return {
            "bolsa": [],
            "torneo": {
                "nombre": "",
                "fecha_hora": "",
                "lugar": "",
                "inscripciones_abiertas": 0,
                "n_canchas": 0,
                "n_bloques": 0,
                "participantes": [],
                "espera": [],
                "resultados": {}
            }
        }

def guardar_datos(datos):
    with open('jugadores.json', 'w') as f:
        json.dump(datos, f)

datos = cargar_datos()

@app.route('/')
def index():
    bolsa_con_indices = [(jugador, i) for i, jugador in enumerate(datos['bolsa'])]
    def get_ranking_key(x):
        try:
            return -float(x[0].get('ranking', '0') or '0')
        except (ValueError, TypeError):
            return 0.0
    bolsa_ordenada = sorted(bolsa_con_indices, key=lambda x: (get_ranking_key(x), x[0]['nombre']))
    return render_template('index.html', torneo=datos['torneo'], bolsa=bolsa_ordenada, participantes=datos['torneo']['participantes'], espera=datos['torneo']['espera'])

@app.route('/acceso_editar_torneo', methods=['GET', 'POST'])
def acceso_editar_torneo():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == PASSWORD_ADMIN:
            return redirect('/editar_torneo')
        return render_template('acceso_editar_torneo.html', error="Contraseña incorrecta.")
    return render_template('acceso_editar_torneo.html')

@app.route('/agregar', methods=['POST'])
def agregar_jugador():
    nombre = request.form['nombre']
    contacto = request.form['contacto']
    categoria = request.form['categoria']
    ranking = request.form['ranking']
    try:
        float(ranking)
    except ValueError:
        return "El ranking debe ser un número.", 400
    datos['bolsa'].append({'nombre': nombre, 'contacto': contacto, 'categoria': categoria, 'ranking': ranking})
    guardar_datos(datos)
    return redirect('/editar_torneo')

@app.route('/importar_tabla', methods=['POST'])
def importar_tabla():
    try:
        jugadores = request.get_json()
        for jugador in jugadores:
            nombre = jugador.get('nombre', '').strip()
            contacto = jugador.get('contacto', '').strip()
            categoria = jugador.get('categoria', '').strip()
            ranking = jugador.get('ranking', '').strip()
            if not nombre or not contacto or not categoria or not ranking:
                continue
            try:
                float(ranking)
            except ValueError:
                continue
            nuevo_jugador = {'nombre': nombre, 'contacto': contacto, 'categoria': categoria, 'ranking': ranking}
            if not any(j['nombre'] == nombre and j['contacto'] == contacto for j in datos['bolsa']):
                datos['bolsa'].append(nuevo_jugador)
        guardar_datos(datos)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/editar/<int:indice>', methods=['GET', 'POST'])
def editar_jugador(indice):
    jugador = datos['bolsa'][indice]
    if request.method == 'POST':
        if 'nombre' in request.form:
            ranking = request.form['ranking']
            try:
                float(ranking)
            except ValueError:
                return render_template('editar.html', jugador=jugador, indice=indice, error="El ranking debe ser un número.", show_contact=True)
            datos['bolsa'][indice] = {
                'nombre': request.form['nombre'],
                'contacto': request.form['contacto'],
                'categoria': request.form['categoria'],
                'ranking': ranking
            }
            guardar_datos(datos)
            return redirect('/editar_torneo')
        return render_template('editar.html', jugador=jugador, indice=indice, show_contact=True)
    return render_template('editar.html', jugador=jugador, indice=indice, show_contact=False)

@app.route('/eliminar/<int:indice>', methods=['GET', 'POST'])
def eliminar_jugador(indice):
    if request.method == 'POST':
        jugador_eliminado = datos['bolsa'].pop(indice)
        datos['torneo']['participantes'] = [p for p in datos['torneo']['participantes'] if p != jugador_eliminado]
        datos['torneo']['espera'] = [p for p in datos['torneo']['espera'] if p != jugador_eliminado]
        if len(datos['torneo']['espera']) > 0 and len(datos['torneo']['participantes']) < datos['torneo']['inscripciones_abiertas']:
            datos['torneo']['participantes'].append(datos['torneo']['espera'].pop(0))
        guardar_datos(datos)
        return redirect('/editar_torneo')
    return render_template('eliminar.html', jugador=datos['bolsa'][indice], indice=indice)

@app.route('/editar_torneo', methods=['GET', 'POST'])
def editar_torneo():
    bolsa_con_indices = [(jugador, i) for i, jugador in enumerate(datos['bolsa'])]
    def get_ranking_key(x):
        try:
            return -float(x[0].get('ranking', '0') or '0')
        except (ValueError, TypeError):
            return 0.0
    bolsa_ordenada = sorted(bolsa_con_indices, key=lambda x: (get_ranking_key(x), x[0]['nombre']))
    if request.method == 'POST':
        datos['torneo']['nombre'] = request.form['nombre']
        datos['torneo']['fecha_hora'] = request.form['fecha_hora']
        datos['torneo']['lugar'] = request.form['lugar']
        datos['torneo']['inscripciones_abiertas'] = int(request.form['inscripciones_abiertas'])
        datos['torneo']['n_canchas'] = int(request.form['n_canchas'])
        datos['torneo']['n_bloques'] = int(request.form['n_bloques'])
        while len(datos['torneo']['participantes']) > datos['torneo']['inscripciones_abiertas']:
            datos['torneo']['espera'].append(datos['torneo']['participantes'].pop())
        while len(datos['torneo']['espera']) > 0 and len(datos['torneo']['participantes']) < datos['torneo']['inscripciones_abiertas']:
            datos['torneo']['participantes'].append(datos['torneo']['espera'].pop(0))
        guardar_datos(datos)
        return redirect('/editar_torneo')
    return render_template('editar_torneo.html', torneo=datos['torneo'], bolsa=bolsa_ordenada)

@app.route('/seleccionar/<int:indice>')
def seleccionar_jugador(indice):
    jugador = datos['bolsa'][indice]
    if jugador not in datos['torneo']['participantes'] and jugador not in datos['torneo']['espera']:
        if len(datos['torneo']['participantes']) < datos['torneo']['inscripciones_abiertas']:
            datos['torneo']['participantes'].append(jugador)
        else:
            datos['torneo']['espera'].append(jugador)
        guardar_datos(datos)
    return redirect('/')

@app.route('/eliminar_participante/<int:indice>', methods=['GET', 'POST'])
def eliminar_participante(indice):
    if request.method == 'POST':
        password = request.form.get('password', '')
        jugador = datos['torneo']['participantes'][indice]
        if password not in [jugador['contacto'], PASSWORD_ADMIN]:
            return render_template('eliminar_participante.html', jugador=jugador, indice=indice, error="Contraseña incorrecta.")
        datos['torneo']['participantes'].pop(indice)
        if len(datos['torneo']['espera']) > 0 and len(datos['torneo']['participantes']) < datos['torneo']['inscripciones_abiertas']:
            datos['torneo']['participantes'].append(datos['torneo']['espera'].pop(0))
        guardar_datos(datos)
        return redirect('/')
    return render_template('eliminar_participante.html', jugador=datos['torneo']['participantes'][indice], indice=indice)

@app.route('/eliminar_espera/<int:indice>', methods=['GET', 'POST'])
def eliminar_espera(indice):
    if request.method == 'POST':
        password = request.form.get('password', '')
        jugador = datos['torneo']['espera'][indice]
        if password not in [jugador['contacto'], PASSWORD_ADMIN]:
            return render_template('eliminar_espera.html', jugador=jugador, indice=indice, error="Contraseña incorrecta.")
        datos['torneo']['espera'].pop(indice)
        guardar_datos(datos)
        return redirect('/')
    return render_template('eliminar_espera.html', jugador=datos['torneo']['espera'][indice], indice=indice)

@app.route('/acceso_lanzar_torneo', methods=['GET', 'POST'])
def acceso_lanzar_torneo():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == PASSWORD_ADMIN:
            return redirect('/lanzar_torneo')
        return render_template('acceso_lanzar_torneo.html', error="Contraseña incorrecta.")
    return render_template('acceso_lanzar_torneo.html')

@app.route('/lanzar_torneo', methods=['GET', 'POST'])
def lanzar_torneo():
    participantes = datos['torneo']['participantes']
    n_canchas = datos['torneo']['n_canchas']

    if request.method == 'POST':
        metodo = request.form.get('metodo', 'aleatorio')
        canchas = [[] for _ in range(n_canchas)]

        if metodo == 'aleatorio':
            participantes_copia = participantes.copy()
            random.shuffle(participantes_copia)
            for i, jugador in enumerate(participantes_copia):
                canchas[i % n_canchas].append(jugador)

        elif metodo == 'manual':
            for i, jugador in enumerate(participantes):
                cancha_idx = int(request.form.get(f'jugador_{i}', 0))
                if 0 <= cancha_idx < n_canchas:
                    canchas[cancha_idx].append(jugador)

        elif metodo == 'mismo_ranking':
            ranking_groups = {}
            for jugador in participantes:
                try:
                    ranking = float(jugador['ranking'])
                except (ValueError, TypeError):
                    ranking = 0.0
                if ranking not in ranking_groups:
                    ranking_groups[ranking] = []
                ranking_groups[ranking].append(jugador)
            grupos = list(ranking_groups.values())
            for grupo in grupos:
                grupo_copia = grupo.copy()
                random.shuffle(grupo_copia)
                for i, jugador in enumerate(grupo_copia):
                    canchas[i % n_canchas].append(jugador)

        elif metodo == 'ranking_promedio':
            participantes_copia = sorted(participantes, key=lambda x: float(x.get('ranking', '0') or '0'))
            for i, jugador in enumerate(participantes_copia):
                canchas[i % n_canchas].append(jugador)
            for _ in range(5):
                promedios = [sum(float(j.get('ranking', '0') or '0') for j in c) / max(len(c), 1) for c in canchas]
                max_idx = promedios.index(max(promedios))
                min_idx = promedios.index(min(promedios))
                if len(canchas[max_idx]) > 1:
                    jugador = canchas[max_idx].pop()
                    canchas[min_idx].append(jugador)

        canchas_info = []
        for cancha in canchas:
            cantidad = len(cancha)
            ranking_promedio = sum(float(j.get('ranking', '0') or '0') for j in cancha) / cantidad if cantidad > 0 else 0.0
            canchas_info.append({
                'jugadores': cancha,
                'cantidad': cantidad,
                'ranking_promedio': round(ranking_promedio, 2)
            })

        return render_template('lanzar_torneo.html', canchas=canchas_info, metodo=metodo, participantes=participantes, n_canchas=n_canchas)

    # GET: Mostrar formulario inicial con conteo inicial en cero
    canchas_iniciales = [{'jugadores': [], 'cantidad': 0, 'ranking_promedio': 0.0} for _ in range(n_canchas)]
    return render_template('lanzar_torneo.html', canchas=canchas_iniciales, metodo='aleatorio', participantes=participantes, n_canchas=n_canchas)

@app.route('/generar_encuentros', methods=['POST'])
def generar_encuentros():
    print(f"Received canchas data: {request.form['canchas']}")
    try:
        canchas = json.loads(request.form['canchas'])
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {request.form['canchas']} - {str(e)}")
        return jsonify({"error": "Invalid JSON data", "details": str(e)}), 400

    def generar_partidos(jugadores):
        n = len(jugadores)
        if n < 4:
            return []

        # Calcular número esperado de partidos
        total_parejas = n * (n - 1) // 2
        partidos_esperados = total_parejas // 2

        # Mezclar jugadores para aleatoriedad inicial
        jugadores = jugadores.copy()
        random.shuffle(jugadores)

        partidos = []
        parejas_usadas = set()
        todas_parejas = list(itertools.combinations(jugadores, 2))

        # Generar partidos hasta usar todas las parejas
        while len(parejas_usadas) < total_parejas and len(todas_parejas) >= 2:
            disponibles = [p for p in todas_parejas if tuple(sorted([p[0]['nombre'], p[1]['nombre']])) not in parejas_usadas]
            if len(disponibles) < 2:
                break

            # Tomar la primera pareja disponible
            pareja1 = disponibles[0]
            p1_key = tuple(sorted([pareja1[0]['nombre'], pareja1[1]['nombre']]))
            parejas_usadas.add(p1_key)
            todas_parejas.remove(pareja1)

            # Buscar una segunda pareja compatible
            for pareja2 in disponibles[1:]:
                p2_key = tuple(sorted([pareja2[0]['nombre'], pareja2[1]['nombre']]))
                if (p2_key not in parejas_usadas and
                    pareja1[0]['nombre'] not in [pareja2[0]['nombre'], pareja2[1]['nombre']] and
                    pareja1[1]['nombre'] not in [pareja2[0]['nombre'], pareja2[1]['nombre']]):
                    partidos.append({
                        'pareja1': [pareja1[0], pareja1[1]],
                        'pareja2': [pareja2[0], pareja2[1]]
                    })
                    parejas_usadas.add(p2_key)
                    todas_parejas.remove(pareja2)
                    break
            else:
                # Si no encontramos pareja2, intentamos con la siguiente pareja1
                continue

        # Mezclar los partidos generados para evitar consecutividad
        random.shuffle(partidos)

        print(f"Cancha con {n} jugadores: {len(partidos)} partidos generados, {len(parejas_usadas)} de {total_parejas} parejas usadas")
        return partidos

    encuentros = []
    for cancha in canchas:
        partidos = generar_partidos(cancha['jugadores'])
        encuentros.append({'partidos': partidos})

    return render_template('encuentros.html', encuentros=encuentros)

@app.route('/guardar_resultados', methods=['POST'])
def guardar_resultados():
    resultados = {}
    for key, value in request.form.items():
        if value:  # Solo procesar si se ingresó un valor
            try:
                partes = key.split('_')
                pareja = partes[0]  # 'p1' o 'p2'
                cancha_idx = int(partes[1])
                partido_idx = int(partes[2])
                set_idx = partes[3]  # 's1', 's2', 's3'
                set_num = int(set_idx[1]) - 1  # Convertir 's1' -> 0, 's2' -> 1, 's3' -> 2

                # Organizar en una estructura
                if cancha_idx not in resultados:
                    resultados[cancha_idx] = {}
                if partido_idx not in resultados[cancha_idx]:
                    resultados[cancha_idx][partido_idx] = {'pareja1': [None]*3, 'pareja2': [None]*3}
                if pareja == 'p1':
                    resultados[cancha_idx][partido_idx]['pareja1'][set_num] = int(value)
                elif pareja == 'p2':
                    resultados[cancha_idx][partido_idx]['pareja2'][set_num] = int(value)
            except (IndexError, ValueError) as e:
                print(f"Error procesando resultado {key}: {e}")
                continue

    # Aquí puedes decidir qué hacer con los resultados
    # Por ahora, los guardamos en datos['torneo']['resultados'] (ajusta según tu estructura)
    datos['torneo']['resultados'] = resultados
    guardar_datos(datos)

    print(f"Resultados guardados: {resultados}")
    return redirect('/lanzar_torneo')  # O donde quieras redirigir después

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)