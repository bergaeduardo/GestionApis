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

    def ejecutar_update(self, sql, params=None):
        cursor = self.conectar()
        if cursor:
            try:
                cursor.execute(sql, params if params else ())
                self.connection.commit()
                return True
            except pyodbc.Error as e:
                logger.error(f"Error al ejecutar el update: {e}")
                return False
            finally:
                cursor.close()
                self.connection.close()

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
