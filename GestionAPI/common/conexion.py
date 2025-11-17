import pyodbc
import logging

logger = logging.getLogger(__name__)

class Conexion:
    def __init__(self, server, database, user, password):
        self.server = server
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def conectar(self):
        try:
            self.connection = pyodbc.connect(
                f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.user};PWD={self.password}'
            )
            if self.connection:
                return self.connection.cursor()
        except pyodbc.Error as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            return None

    def ejecutar_consulta(self, sql):
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                resultados = cursor.fetchall()
                self.connection.commit()
                return resultados
            except pyodbc.Error as e:
                logger.error(f"Error al ejecutar la consulta: {e}")
            finally:
                cursor.close()
                self.connection.close()

    def ejecutar_consulta_con_parametros(self, sql, params=None):
        """
        Ejecuta una consulta SELECT con parámetros.
        
        Args:
            sql (str): Consulta SQL
            params (list): Lista de parámetros para la consulta
            
        Returns:
            list: Resultados de la consulta o None si hay error
        """
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql, params if params else ())
                resultados = cursor.fetchall()
                self.connection.commit()
                return resultados
            except pyodbc.Error as e:
                logger.error(f"Error al ejecutar la consulta con parámetros: {e}")
                logger.error(f"SQL: {sql}")
                logger.error(f"Parámetros: {params}")
                return None
            finally:
                cursor.close()
                self.connection.close()
        return None

    def ejecutar_update(self, sql, params=None, max_retries=3):
        cursor = self.conectar()
        if cursor:
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    cursor.execute(sql, params if params else ())
                    self.connection.commit()
                    cursor.close()
                    self.connection.close()
                    return True
                except pyodbc.Error as e:
                    error_code = e.args[0] if e.args else None
                    
                    # Si es un deadlock (código 40001 o 1205), reintentar
                    if error_code in ('40001', '1205') and retry_count < max_retries:
                        retry_count += 1
                        logger.warning(f"Deadlock detectado. Reintentando ({retry_count}/{max_retries})...")
                        import time
                        time.sleep(1 * retry_count)  # Esperar 1, 2, 3 segundos
                        continue
                    
                    logger.error(f"Error al ejecutar el update: {e}")
                    if cursor:
                        cursor.close()
                    if self.connection:
                        self.connection.close()
                    return False
                except Exception as e:
                    logger.error(f"Error inesperado al ejecutar el update: {e}")
                    if cursor:
                        cursor.close()
                    if self.connection:
                        self.connection.close()
                    return False
            
            # Si llegamos aquí, se agotaron los reintentos
            logger.error(f"Se agotaron los reintentos ({max_retries}) para el update")
            if cursor:
                cursor.close()
            if self.connection:
                self.connection.close()
            return False
        
        return False

    def obtener_nombres_columnas(self, sql):
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                columnas = [column[0] for column in cursor.description]
                self.connection.commit()
                return columnas
            except pyodbc.Error as e:
                logger.error(f"Error al obtener los nombres de las columnas: {e}")
                return None
            finally:
                cursor.close()
                self.connection.close()

    def actEstadoSync(self, comprobante):
        resultado = False
        sql = ''' 
                UPDATE EB_T_HistorialSincVentas_Solar 
                SET ESTADO_SYNC = 1, FECHA_SYNC = GETDATE()
                WHERE N_COMP in ''' + comprobante
        
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                self.connection.commit()
                resultado = True
                logger.info(f'Consulta ejecutada con éxito: {sql}')
            except pyodbc.Error as e:
                logger.error(f"Error al ejecutar la consulta: {e}")
                logger.error(f"SQL: {sql}")
            finally:
                cursor.close()
                self.connection.close()
        return resultado
