import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import json

# Centralización de selectores y configuraciones
CONFIGURACION = {
    'url_base': "https://www.paginasamarillas.es/search/profesionales/all-ma/all-pr/all-is/all-ci/all-ba/all-pu/all-nc/",
    'parametro_busqueda': "profesionales",
    'max_intentos_fallidos': 5,
    'cabeceras': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    },
    'selectores': {
        'listado_item': 'div.listado-item',
        'web': 'a.web',
        'direccion': {
            'contenedor': 'div.adress-row',
            'calle': 'span[itemprop="streetAddress"]',
            'codigo_postal': 'span[itemprop="postalCode"]',
            'ciudad': 'span[itemprop="addressLocality"]'
        },
        'telefono': 'span[itemprop="telephone"]',
        'mensaje_no_resultados': 'div.text-center'
    }
}

def raspar_paginas_amarillas(num_paginas=1):
    """
    Raspa los datos de empresas de PáginasAmarillas.es.
    
    :param num_paginas: Número de páginas a raspar (por defecto 1).
    :return: Lista de diccionarios con la información de las empresas.
    """
    resultados = []
    intentos_fallidos_consecutivos = 0

    for pagina in range(1, num_paginas + 1):
        url = f"{CONFIGURACION['url_base']}{pagina}?what={CONFIGURACION['parametro_busqueda']}"
        print(f"Raspando página {pagina}: {url}")
        
        try:
            time.sleep(random.uniform(2, 5))  # Pausa aleatoria para evitar sobrecarga del servidor
            
            respuesta = requests.get(url, headers=CONFIGURACION['cabeceras'])
            respuesta.raise_for_status()
            respuesta.encoding = 'utf-8'
            
            sopa = BeautifulSoup(respuesta.text, 'html.parser')
            
            listados = sopa.select(CONFIGURACION['selectores']['listado_item'])
            print(f"Encontrados {len(listados)} listados en la página {pagina}")
            
            if not listados:
                intentos_fallidos_consecutivos = manejar_pagina_sin_resultados(sopa, intentos_fallidos_consecutivos)
                if intentos_fallidos_consecutivos >= CONFIGURACION['max_intentos_fallidos']:
                    break
            else:
                intentos_fallidos_consecutivos = 0  # Reiniciar el contador si se encuentran resultados
                for item in listados:
                    resultados.append(extraer_datos_empresa(item))
                
        except requests.RequestException as e:
            print(f"Error al hacer la solicitud a la página {pagina}: {e}")
            intentos_fallidos_consecutivos = manejar_error(intentos_fallidos_consecutivos)
            if intentos_fallidos_consecutivos >= CONFIGURACION['max_intentos_fallidos']:
                break
        
        except Exception as e:
            print(f"Error inesperado al procesar la página {pagina}: {e}")
            intentos_fallidos_consecutivos = manejar_error(intentos_fallidos_consecutivos)
            if intentos_fallidos_consecutivos >= CONFIGURACION['max_intentos_fallidos']:
                break
    
    return resultados

def manejar_pagina_sin_resultados(sopa, intentos_fallidos):
    """
    Maneja el caso cuando no se encuentran listados en una página.
    
    :param sopa: Objeto BeautifulSoup de la página
    :param intentos_fallidos: Número actual de intentos fallidos consecutivos
    :return: Número actualizado de intentos fallidos consecutivos
    """
    print("No se encontraron listados. Verificando si hay un mensaje de no resultados...")
    mensaje_no_resultados = sopa.select_one(CONFIGURACION['selectores']['mensaje_no_resultados'])
    if mensaje_no_resultados:
        print(f"Mensaje encontrado: {mensaje_no_resultados.text.strip()}")
    else:
        print("No se encontró un mensaje de 'no resultados'. La estructura de la página podría haber cambiado.")
    
    return intentos_fallidos + 1

def manejar_error(intentos_fallidos):
    """
    Maneja errores incrementando el contador de intentos fallidos.
    
    :param intentos_fallidos: Número actual de intentos fallidos consecutivos
    :return: Número actualizado de intentos fallidos consecutivos
    """
    intentos_fallidos += 1
    if intentos_fallidos >= CONFIGURACION['max_intentos_fallidos']:
        print("Se alcanzó el máximo de intentos fallidos consecutivos. Finalizando el proceso.")
    return intentos_fallidos

def extraer_datos_empresa(item):
    """
    Extrae los datos relevantes de un listado de empresa.
    
    :param item: Elemento BeautifulSoup que contiene los datos de la empresa
    :return: Diccionario con los datos extraídos de la empresa
    """
    # Extraer datos de data-analytics
    data_analytics = json.loads(item.get('data-analytics', '{}'))
    actividad = data_analytics.get('activity', 'N/A')
    nombre = data_analytics.get('name', 'N/A')
    provincia = data_analytics.get('province', 'N/A')
    
    # Extraer sitio web
    etiqueta_web = item.select_one(CONFIGURACION['selectores']['web'])
    sitio_web = etiqueta_web['href'] if etiqueta_web else 'N/A'
    
    # Extraer dirección, código postal y ciudad
    address_row = item.select_one(CONFIGURACION['selectores']['direccion']['contenedor'])
    if address_row:
        direccion = address_row.select_one(CONFIGURACION['selectores']['direccion']['calle']).text.strip() if address_row.select_one(CONFIGURACION['selectores']['direccion']['calle']) else 'N/A'
        codigo_postal = address_row.select_one(CONFIGURACION['selectores']['direccion']['codigo_postal']).text.strip() if address_row.select_one(CONFIGURACION['selectores']['direccion']['codigo_postal']) else 'N/A'
        ciudad = address_row.select_one(CONFIGURACION['selectores']['direccion']['ciudad']).text.strip() if address_row.select_one(CONFIGURACION['selectores']['direccion']['ciudad']) else 'N/A'
    else:
        direccion = codigo_postal = ciudad = 'N/A'
    
    # Extraer teléfono
    telefono_span = item.select_one(CONFIGURACION['selectores']['telefono'])
    telefono = telefono_span.text.strip() if telefono_span else 'N/A'
    
    return {
        'Nombre': nombre,
        'Actividad': actividad,
        'Provincia': provincia,
        'Dirección': direccion,
        'Código Postal': codigo_postal,
        'Ciudad': ciudad,
        'Teléfono': telefono,
        'Sitio Web': sitio_web
    }

def guardar_en_csv(datos, nombre_archivo):
    """
    Guarda los datos raspados en un archivo CSV.
    
    :param datos: Lista de diccionarios con la información de las empresas.
    :param nombre_archivo: Nombre del archivo CSV donde se guardarán los datos.
    """
    if not datos:
        print("No hay datos para guardar en el CSV.")
        return
    
    claves = datos[0].keys()
    with open(nombre_archivo, 'w', newline='', encoding='utf-8-sig') as archivo_salida:
        escritor_dict = csv.DictWriter(archivo_salida, claves)
        escritor_dict.writeheader()
        escritor_dict.writerows(datos)

# Ejemplo de uso del script
if __name__ == "__main__":
    num_paginas = 6000  # Ajusta esto según la cantidad de páginas que quieras raspar
    resultados = raspar_paginas_amarillas(num_paginas)

    if resultados:
        guardar_en_csv(resultados, 'resultados_profesionales_paginas_amarillas.csv')
        print(f"Se han extraído {len(resultados)} resultados y guardado en 'resultados_profesionales_paginas_amarillas.csv' con codificación UTF-8")
    else:
        print("No se encontraron resultados para guardar.")