import pyodbc
import logging

logger = logging.getLogger('solar_sync')

class DatabaseConnection:
    def __init__(self, server, database, user, password):
        self.server = server
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def conectar(self):
        try:
            self.connection = pyodbc.connect(
                f'DRIVER={{ODBC Driver 13 for SQL Server}};SERVER={self.server};'
                f'DATABASE={self.database};UID={self.user};PWD={self.password}'
            )
            logger.debug("Conexión establecida con la base de datos")
            return self.connection.cursor()
        except pyodbc.Error as e:
            logger.error(f"Error al conectar a la base de datos: {str(e)}")
            return None

    def ejecutar_consulta(self, sql):
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                resultados = cursor.fetchall()
                self.connection.commit()
                logger.debug(f"Consulta ejecutada exitosamente: {sql[:100]}...")
                return resultados
            except pyodbc.Error as e:
                logger.error(f"Error al ejecutar la consulta: {str(e)}")
                return None
            finally:
                cursor.close()
                self.connection.close()

    def obtener_nombres_columnas(self, sql):
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                columnas = [column[0] for column in cursor.description]
                logger.debug("Nombres de columnas obtenidos correctamente")
                return columnas
            except pyodbc.Error as e:
                logger.error(f"Error al obtener nombres de columnas: {str(e)}")
                return None
            finally:
                cursor.close()
                self.connection.close()

    def actualizar_estado_sync(self, comprobantes):
        sql = ''' 
                UPDATE EB_T_HistorialSincVentas_Solar 
                SET ESTADO_SYNC = 1, FECHA_SYNC = GETDATE()
                WHERE N_COMP in ''' + comprobantes
        
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql)
                self.connection.commit()
                logger.info(f"Estado de sincronización actualizado para comprobantes: {comprobantes}")
                return True
            except pyodbc.Error as e:
                logger.error(f"Error al actualizar estado de sincronización: {str(e)}")
                return False
            finally:
                cursor.close()
                self.connection.close()