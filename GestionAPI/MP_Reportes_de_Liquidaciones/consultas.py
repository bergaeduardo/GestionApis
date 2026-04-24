"""
Consultas y constantes SQL para el módulo MP-Reportes_de_Liquidaciones.
Define el mapeo de columnas CSV → tabla SQL y el template MERGE.
"""

# Nombre de la tabla destino
TABLE_NAME = "MP_T_REPORTE_DE_LIQUIDACIONES"

# Columnas clave usadas en el ON del MERGE (identifica unicidad de registro)
MERGE_KEY_COLUMNS = ["FECHA_LIQUIDACION", "SOURCE_ID", "RECORD_TYPE", "DESCRIPTION"]

# Mapeo: nombre de columna en el CSV (KEY del reporte en inglés) → columna en la tabla SQL
# Formato: "CSV_KEY": "COLUMNA_DB"
CSV_TO_DB_COLUMNS = {
    "DATE":                         "FECHA_LIQUIDACION",
    "SOURCE_ID":                    "SOURCE_ID",
    "EXTERNAL_REFERENCE":           "EXTERNAL_REFERENCE",
    "RECORD_TYPE":                  "RECORD_TYPE",
    "DESCRIPTION":                  "DESCRIPTION",
    "NET_CREDIT_AMOUNT":            "NET_CREDIT_AMOUNT",
    "NET_DEBIT_AMOUNT":             "NET_DEBIT_AMOUNT",
    "SELLER_AMOUNT":                "SELLER_AMOUNT",
    "GROSS_AMOUNT":                 "GROSS_AMOUNT",
    "METADATA":                     "METADATA",
    "MP_FEE_AMOUNT":                "MP_FEE_AMOUNT",
    "FINANCING_FEE_AMOUNT":         "FINANCING_FEE_AMOUNT",
    "SHIPPING_FEE_AMOUNT":          "SHIPPING_FEE_AMOUNT",
    "TAXES_AMOUNT":                 "TAXES_AMOUNT",
    "COUPON_AMOUNT":                "COUPON_AMOUNT",
    "INSTALLMENTS":                 "INSTALLMENTS",
    "PAYMENT_METHOD":               "PAYMENT_METHOD",
    "PAYMENT_METHOD_TYPE":          "PAYMENT_METHOD_TYPE",
    "TAX_DETAIL":                   "TAX_DETAIL",
    "TAX_AMOUNT_TELCO":             "TAX_AMOUNT_TELCO",
    "TRANSACTION_APPROVAL_DATE":    "TRANSACTION_APPROVAL_DATE",
    "POS_ID":                       "POS_ID",
    "POS_NAME":                     "POS_NAME",
    "EXTERNAL_POS_ID":              "EXTERNAL_POS_ID",
    "STORE_ID":                     "STORE_ID",
    "STORE_NAME":                   "STORE_NAME",
    "EXTERNAL_STORE_ID":            "EXTERNAL_STORE_ID",
    "ORDER_ID":                     "ORDER_ID",
    "SHIPPING_ID":                  "SHIPPING_ID",
    "SHIPMENT_MODE":                "SHIPMENT_MODE",
    "PACK_ID":                      "PACK_ID",
    "TAXES_DISAGGREGATED":          "TAXES_DISAGGREGATED",
    "EFFECTIVE_COUPON_AMOUNT":      "EFFECTIVE_COUPON_AMOUNT",
    "POI_ID":                       "POI_ID",
    "CARD_INITIAL_NUMBER":          "CARD_INITIAL_NUMBER",
    "OPERATION_TAGS":               "OPERATION_TAGS",
    "ITEM_ID":                      "ITEM_ID",
    "PAYER_NAME":                   "PAYER_NAME",
    "PAYER_ID_TYPE":                "PAYER_ID_TYPE",
    "PAYER_ID_NUMBER":              "PAYER_ID_NUMBER",
    "BUSINESS_UNIT":                "BUSINESS_UNIT",
    "SUB_UNIT":                     "SUB_UNIT",
    "BALANCE_AMOUNT":               "BALANCE_AMOUNT",
    "PAYOUT_BANK_ACCOUNT_NUMBER":   "PAYOUT_BANK_ACCOUNT_NUMBER",
    "PRODUCT_SKU":                  "PRODUCT_SKU",
    "SALE_DETAIL":                  "SALE_DETAIL",
    "CURRENCY":                     "CURRENCY",
    "FRANCHISE":                    "FRANCHISE",
    "LAST_FOUR_DIGITS":             "LAST_FOUR_DIGITS",
    "ORDER_MP":                     "ORDER_MP",
    "POI_WALLET_NAME":              "POI_WALLET_NAME",
    "TRANSACTION_INTENT_ID":        "TRANSACTION_INTENT_ID",
    "POI_BANK_NAME":                "POI_BANK_NAME",
    "PURCHASE_ID":                  "PURCHASE_ID",
    "IS_RELEASED":                  "IS_RELEASED",
    "SHIPPING_ORDER_ID":            "SHIPPING_ORDER_ID",
    "ISSUER_NAME":                  "ISSUER_NAME",
}

# Columnas con tipo numérico decimal (para conversión en Pandas)
DECIMAL_COLUMNS = {
    "NET_CREDIT_AMOUNT", "NET_DEBIT_AMOUNT", "SELLER_AMOUNT", "GROSS_AMOUNT",
    "MP_FEE_AMOUNT", "FINANCING_FEE_AMOUNT", "SHIPPING_FEE_AMOUNT", "TAXES_AMOUNT",
    "COUPON_AMOUNT", "EFFECTIVE_COUPON_AMOUNT", "TAX_AMOUNT_TELCO", "BALANCE_AMOUNT",
}

# Columnas con tipo entero
INT_COLUMNS = {
    "INSTALLMENTS", "ORDER_ID", "SHIPPING_ID", "PACK_ID",
}

# Columnas con tipo datetime
DATETIME_COLUMNS = {
    "DATE", "TRANSACTION_APPROVAL_DATE",
}

# Columnas booleanas
BOOL_COLUMNS = {
    "IS_RELEASED",
}
