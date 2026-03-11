#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sincronización de rótulos Andreani — Pedidos desde Sucursal.

Este script gestiona el proceso de creación de órdenes de envío y generación
de etiquetas para pedidos que se entregan directamente desde el punto de
venta (sucursal). Los datos se leen desde la tabla EB_ENVIOS_WEB_DESDE_SUC.

A diferencia de sync_rotulos_andreani.py, este script NO realiza impresión.
Una vez obtenida la etiqueta se registra en el log y se actualiza IMP_ROT = 1.
"""

import asyncio
import platform
import json
import sys
import os
import logging

# Configuración de rutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from GestionAPI.Andreani.andreani_api import AndreaniAPI
from GestionAPI.Andreani.db_operations_andreani import AndreaniSucDB
from GestionAPI.common.credenciales import DATA_PROD as DATA_PROD
from GestionAPI.common.logger_config import setup_logger

# Configuración del logger
logger = setup_logger('andreani_rotulos_suc')

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def process_orders_and_get_labels() -> None:
    """
    Función principal que maneja el proceso de obtención y generación de etiquetas
    para pedidos entregados desde sucursal.
    Consulta EB_ENVIOS_WEB_DESDE_SUC por pedidos pendientes, crea las órdenes de
    envío, obtiene las etiquetas y actualiza IMP_ROT = 1 en la base de datos.
    """
    base_url = DATA_PROD["url"]
    user = DATA_PROD["user"]
    password = DATA_PROD["passw"]

    # Inicialización de la API
    try:
        api = AndreaniAPI(base_url, user, password)
        logger.info("Conexión exitosa a la API de Andreani")
    except ValueError as e:
        logger.error(f"Error al inicializar la API de Andreani: {e}")
        return

    try:
        andreani_db = AndreaniSucDB()
        logger.info("Conexión exitosa a la base de datos")

        # Lista para almacenar los pedidos a los que se les solicitará etiqueta
        orders_to_process = []

        # ------------------------------------------------------------------ #
        # PASO 1: Pedidos con número de envío ya creado pero IMP_ROT pendiente
        # ------------------------------------------------------------------ #
        pedidos_pendientes = andreani_db.get_pedidos_sin_imprimir()

        if pedidos_pendientes:
            logger.info(
                f"Procesando {len(pedidos_pendientes)} pedidos con envío creado "
                f"pendientes de etiqueta"
            )
            for pedido_data in pedidos_pendientes:
                nro_pedido = pedido_data[0].strip() if pedido_data[0] else None
                num_seguimiento = pedido_data[1].strip() if pedido_data[1] else None

                if nro_pedido and num_seguimiento:
                    orders_to_process.append({
                        "numeroPedido": nro_pedido,
                        "numeroEnvio": num_seguimiento,
                        "numeroAgrupador": num_seguimiento,
                    })
                    logger.info(
                        f"Pedido pendiente agregado — "
                        f"Pedido: {nro_pedido}, Envío: {num_seguimiento}"
                    )

        # ------------------------------------------------------------------ #
        # PASO 2: Nuevos pedidos (sin número de envío)
        # ------------------------------------------------------------------ #
        datos_db = andreani_db.get_data_from_suc()

        if datos_db:
            json_string = datos_db[0][0]
            if json_string:
                orders_data = json.loads(json_string)
                orders = orders_data.get("data", [])

                if orders:
                    logger.info(f"Se encontraron {len(orders)} pedidos nuevos para procesar")

                    create_order_tasks = []

                    for order in orders:
                        # Normalizar estructura postal devuelta por SQL Server
                        if (
                            "origen" in order
                            and "postal" in order["origen"]
                            and isinstance(order["origen"]["postal"], list)
                        ):
                            order["origen"]["postal"] = order["origen"]["postal"][0]
                        if (
                            "destino" in order
                            and "postal" in order["destino"]
                            and isinstance(order["destino"]["postal"], list)
                        ):
                            order["destino"]["postal"] = order["destino"]["postal"][0]

                        create_order_tasks.append(api.crear_orden_envio(order))

                    orders_results = await asyncio.gather(
                        *create_order_tasks, return_exceptions=True
                    )

                    for order, result in zip(orders, orders_results):
                        if isinstance(result, Exception):
                            logger.error(f"Error al crear orden de envío: {result}")
                            continue

                        if result is None:
                            logger.error(
                                f"No se pudo crear la orden de envío para el pedido "
                                f"{order.get('idPedido')}, el resultado de la API fue nulo."
                            )
                            continue

                        numero_envio = result.get("numeroEnvio")
                        numero_agrupador = result.get("numeroAgrupador")
                        numero_pedido = order.get("idPedido", "No especificado")

                        if numero_agrupador and numero_envio:
                            if andreani_db.update_num_seguimiento(numero_pedido, numero_envio):
                                logger.info(
                                    f"Orden creada y NUM_SEGUIMIENTO guardado — "
                                    f"Pedido: {numero_pedido}, Envío: {numero_envio}, "
                                    f"Agrupador: {numero_agrupador}"
                                )
                                orders_to_process.append({
                                    "numeroPedido": numero_pedido,
                                    "numeroEnvio": numero_envio,
                                    "numeroAgrupador": numero_agrupador,
                                })
                            else:
                                logger.error(
                                    f"No se pudo guardar NUM_SEGUIMIENTO para el pedido {numero_pedido}"
                                )
            else:
                logger.debug("No hay datos JSON para procesar nuevos pedidos.")

        # ------------------------------------------------------------------ #
        # PASO 3: Verificar si hay pedidos a procesar
        # ------------------------------------------------------------------ #
        if not orders_to_process:
            logger.info("No hay pedidos para procesar en este momento")
            return

        logger.info(
            f"Total de pedidos a procesar para generación de etiquetas: {len(orders_to_process)}"
        )

        # ------------------------------------------------------------------ #
        # PASO 4: Obtener etiquetas y actualizar IMP_ROT
        # ------------------------------------------------------------------ #
        label_tasks = [
            api.obtener_etiquetas(order_info["numeroAgrupador"])
            for order_info in orders_to_process
        ]

        labels_results = await asyncio.gather(*label_tasks, return_exceptions=True)

        for order_info, label_result in zip(orders_to_process, labels_results):
            if isinstance(label_result, Exception):
                logger.error(
                    f"Error al obtener etiqueta para el pedido "
                    f"{order_info['numeroPedido']}: {label_result}"
                )
                continue

            if label_result is None:
                logger.error(
                    f"Etiqueta nula para el pedido {order_info['numeroPedido']}"
                )
                continue

            logger.info(
                f"[OK] Etiqueta generada correctamente — "
                f"Pedido: {order_info['numeroPedido']}, Envío: {order_info['numeroEnvio']}"
            )

            if andreani_db.update_imp_rot(order_info["numeroPedido"]):
                logger.info(
                    f"[OK] Base de datos actualizada (IMP_ROT=1) — "
                    f"Pedido: {order_info['numeroPedido']}"
                )
            else:
                logger.error(
                    f"[ERROR] No se pudo actualizar IMP_ROT en la base de datos — "
                    f"Pedido: {order_info['numeroPedido']}"
                )

    except Exception as e:
        logger.error(f"Error general en el proceso: {e}")


if __name__ == "__main__":
    logger.info("Iniciando proceso de sincronización de rótulos Andreani (desde sucursal)")
    asyncio.run(process_orders_and_get_labels())
    logger.info("Proceso de sincronización de rótulos Andreani (desde sucursal) finalizado")
