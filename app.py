from flask import Flask, render_template, request, redirect, jsonify, send_file
import json
import random
import itertools
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

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
            if "estadisticas" not in data["torneo"]:
                data["torneo"]["estadisticas"] = {}
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
                "resultados": {},
                "estadisticas": {}
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

        total_parejas = n * (n - 1) // 2
        partidos_esperados = total_parejas // 2

        jugadores = jugadores.copy()
        random.shuffle(jugadores)

        partidos = []
        parejas_usadas = set()
        todas_parejas = list(itertools.combinations(jugadores, 2))

        while len(parejas_usadas) < total_parejas and len(todas_parejas) >= 2:
            disponibles = [p for p in todas_parejas if tuple(sorted([p[0]['nombre'], p[1]['nombre']])) not in parejas_usadas]
            if len(disponibles) < 2:
                break

            pareja1 = disponibles[0]
            p1_key = tuple(sorted([pareja1[0]['nombre'], pareja1[1]['nombre']]))
            parejas_usadas.add(p1_key)
            todas_parejas.remove(pareja1)

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
                continue

        def reordenar_partidos(partidos):
            random.shuffle(partidos)
            max_consecutivos = 2
            intentos = 100

            for _ in range(intentos):
                valido = True
                jugadores_vistos = {}
                for i, partido in enumerate(partidos):
                    nombres = [partido['pareja1'][0]['nombre'], partido['pareja1'][1]['nombre'],
                               partido['pareja2'][0]['nombre'], partido['pareja2'][1]['nombre']]
                    for nombre in nombres:
                        if nombre not in jugadores_vistos:
                            jugadores_vistos[nombre] = []
                        jugadores_vistos[nombre].append(i)
                        if len(jugadores_vistos[nombre]) > max_consecutivos:
                            ultimos = jugadores_vistos[nombre][-max_consecutivos-1:]
                            if ultimos[-1] - ultimos[0] == max_consecutivos:
                                valido = False
                                if i < len(partidos) - 1:
                                    swap_idx = random.randint(i + 1, len(partidos) - 1)
                                    partidos[i], partidos[swap_idx] = partidos[swap_idx], partidos[i]
                                break
                    if not valido:
                        break
                if valido:
                    break
            return partidos

        partidos = reordenar_partidos(partidos)
        print(f"Cancha con {n} jugadores: {len(partidos)} partidos generados, {len(parejas_usadas)} de {total_parejas} parejas usadas")
        return partidos

    encuentros = []
    for cancha in canchas:
        partidos = generar_partidos(cancha['jugadores'])
        encuentros.append({'partidos': partidos})

    datos['torneo']['encuentros'] = encuentros
    guardar_datos(datos)
    return render_template('encuentros.html', encuentros=encuentros)

@app.route('/guardar_resultados_parciales', methods=['POST'])
def guardar_resultados_parciales():
    resultados = {}
    for key, value in request.form.items():
        if value.strip():
            try:
                partes = key.split('_')
                pareja = partes[0]
                cancha_idx = int(partes[1])
                partido_idx = int(partes[2])
                set_idx = partes[3]
                set_num = int(set_idx[1]) - 1

                if cancha_idx not in resultados:
                    resultados[cancha_idx] = {}
                if partido_idx not in resultados[cancha_idx]:
                    resultados[cancha_idx][partido_idx] = {'pareja1': [None]*3, 'pareja2': [None]*3}
                if pareja == 'p1':
                    resultados[cancha_idx][partido_idx]['pareja1'][set_num] = int(value)
                elif pareja == 'p2':
                    resultados[cancha_idx][partido_idx]['pareja2'][set_num] = int(value)
            except (IndexError, ValueError) as e:
                print(f"Error procesando resultado parcial {key}: {e}")
                continue

    datos['torneo']['resultados'].update(resultados)
    guardar_datos(datos)
    print(f"Resultados parciales guardados: {resultados}")
    return jsonify({"status": "success", "message": "Resultados parciales guardados"})

@app.route('/finalizar_torneo', methods=['POST'])
def finalizar_torneo():
    resultados = {}
    encuentros = datos['torneo'].get('encuentros', [])
    for key, value in request.form.items():
        try:
            partes = key.split('_')
            pareja = partes[0]
            cancha_idx = int(partes[1])
            partido_idx = int(partes[2])
            set_idx = partes[3]
            set_num = int(set_idx[1]) - 1

            if cancha_idx not in resultados:
                resultados[cancha_idx] = {}
            if partido_idx not in resultados[cancha_idx]:
                resultados[cancha_idx][partido_idx] = {'pareja1': [0]*3, 'pareja2': [0]*3}
            if pareja == 'p1':
                resultados[cancha_idx][partido_idx]['pareja1'][set_num] = int(value) if value.strip() else 0
            elif pareja == 'p2':
                resultados[cancha_idx][partido_idx]['pareja2'][set_num] = int(value) if value.strip() else 0
        except (IndexError, ValueError) as e:
            print(f"Error procesando resultado final {key}: {e}")
            continue

    datos['torneo']['resultados'] = resultados
    resultados_texto = generar_resultados_texto(resultados, encuentros)
    with open('resultados.txt', 'w') as f:
        f.write(resultados_texto)
    generar_resultados_html(resultados_texto)
    generar_resultados_pdf(resultados_texto)

    estadisticas = calcular_estadisticas(resultados, encuentros)
    datos['torneo']['estadisticas'] = estadisticas
    guardar_datos(datos)

    # Actualizar ranking en la bolsa de jugadores
    for cancha_idx, jugadores_stats in estadisticas.items():
        for nombre, stats in jugadores_stats.items():
            for i, jugador in enumerate(datos['bolsa']):
                if jugador['nombre'] == nombre:
                    current_ranking = float(jugador.get('ranking', '0') or '0')
                    nuevo_ranking = current_ranking + stats['plus_rk']
                    datos['bolsa'][i]['ranking'] = str(round(nuevo_ranking, 2))
                    break

    guardar_datos(datos)
    return render_template('resultados.html', estadisticas=estadisticas)

@app.route('/resetear_torneo')
def resetear_torneo():
    datos['torneo'] = {
        "nombre": "",
        "fecha_hora": "",
        "lugar": "",
        "inscripciones_abiertas": 0,
        "n_canchas": 0,
        "n_bloques": 0,
        "participantes": [],
        "espera": [],
        "resultados": {},
        "estadisticas": {}
    }
    guardar_datos(datos)
    return redirect('/')

def generar_resultados_texto(resultados, encuentros):
    texto = "Resultados del Torneo\n\n"
    for cancha_idx, partidos in resultados.items():
        texto += f"Cancha {cancha_idx + 1}\n"
        for partido_idx, datos in partidos.items():
            pareja1 = encuentros[cancha_idx]['partidos'][partido_idx]['pareja1']
            pareja2 = encuentros[cancha_idx]['partidos'][partido_idx]['pareja2']
            texto += f"  Partido {partido_idx + 1}: {pareja1[0]['nombre']}/{pareja1[1]['nombre']} {datos['pareja1']} vs {pareja2[0]['nombre']}/{pareja2[1]['nombre']} {datos['pareja2']}\n"
        texto += "\n"
    return texto

def generar_resultados_html(texto):
    html = f"<html><body><pre>{texto}</pre></body></html>"
    with open('resultados.html', 'w') as f:
        f.write(html)

def generar_resultados_pdf(texto):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(line, styles['Normal']) if line.strip() else Spacer(1, 12) for line in texto.split('\n')]
    doc.build(story)
    buffer.seek(0)
    with open('resultados.pdf', 'wb') as f:
        f.write(buffer.getvalue())

def calcular_estadisticas(resultados, encuentros):
    estadisticas = {}
    for cancha_idx, partidos in resultados.items():
        estadisticas[cancha_idx] = {}
        jugadores_stats = {}
        for partido_idx, datos in partidos.items():
            pareja1 = encuentros[cancha_idx]['partidos'][partido_idx]['pareja1']
            pareja2 = encuentros[cancha_idx]['partidos'][partido_idx]['pareja2']
            nombres_p1 = [pareja1[0]['nombre'], pareja1[1]['nombre']]
            nombres_p2 = [pareja2[0]['nombre'], pareja2[1]['nombre']]
            sets_p1 = datos['pareja1']
            sets_p2 = datos['pareja2']

            games_ganados_p1 = sum(sets_p1)
            games_ganados_p2 = sum(sets_p2)
            wins_p1 = sum(1 for i in range(3) if sets_p1[i] > sets_p2[i])
            wins_p2 = sum(1 for i in range(3) if sets_p2[i] > sets_p1[i])

            for nombre in nombres_p1:
                if nombre not in jugadores_stats:
                    jugadores_stats[nombre] = {'W': 0, 'L': 0, 'T': 0, 'games_ganados': 0, 'games_perdidos': 0}
                jugadores_stats[nombre]['games_ganados'] += games_ganados_p1
                jugadores_stats[nombre]['games_perdidos'] += games_ganados_p2
                if wins_p1 > wins_p2:
                    jugadores_stats[nombre]['W'] += 1
                elif wins_p2 > wins_p1:
                    jugadores_stats[nombre]['L'] += 1
                else:
                    jugadores_stats[nombre]['T'] += 1

            for nombre in nombres_p2:
                if nombre not in jugadores_stats:
                    jugadores_stats[nombre] = {'W': 0, 'L': 0, 'T': 0, 'games_ganados': 0, 'games_perdidos': 0}
                jugadores_stats[nombre]['games_ganados'] += games_ganados_p2
                jugadores_stats[nombre]['games_perdidos'] += games_ganados_p1
                if wins_p2 > wins_p1:
                    jugadores_stats[nombre]['W'] += 1
                elif wins_p1 > wins_p2:
                    jugadores_stats[nombre]['L'] += 1
                else:
                    jugadores_stats[nombre]['T'] += 1

        for nombre, stats in jugadores_stats.items():
            stats['diff'] = stats['games_ganados'] - stats['games_perdidos']
            stats['plus_rk'] = (2 * stats['W']) + stats['T'] + (0.01 * stats['diff'])  # Cambiado de 0.1 a 0.01
        estadisticas[cancha_idx] = dict(sorted(jugadores_stats.items(), key=lambda x: (x[1]['W'], x[1]['diff'], x[1]['T']), reverse=True))

    return estadisticas

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)