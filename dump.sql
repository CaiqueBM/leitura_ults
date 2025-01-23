BEGIN TRANSACTION;
CREATE TABLE consumos (
    UNIDADE_EDP TEXT,
    MES_DE_CONSUMO TEXT,
    MONTANTE REAL,
    VALOR_FATURA REAL,
    BANDEIRA TEXT
, "QUANT_DIAS_BANDEIRA"	INTEGER);
CREATE TABLE "geracoes" (
	"UNIDADE_EDP"	TEXT,
	"MES_PRODUCAO"	TEXT,
	"LEITURA_TELEM"	REAL,
	"LEITURA_FATURA"	TEXT,
	"CONSUMO"	REAL,
	"FATURAMENTO"	REAL,
	"UNID_CONSUMIDORA"	TEXT,
	"ALUGUEL_PAGO"	BLOB DEFAULT 'FALSE'
);
CREATE TABLE "historico" (
	"UNIDADE_EDP"	TEXT,
	"MES_DE_CONSUMO"	TEXT,
	"MONTANTE"	REAL,
	"VALOR_FATURA"	REAL,
	"VALOR_CONTRATADO"	REAL,
	"MONTANTE_CONT"	REAL,
	"ECONOMIA"	REAL,
	"VALOR_KWH"	REAL,
	"TEM_FATURA"	BLOB
);
CREATE TABLE "nomes" (
	"UNIDADE_EDP"	TEXT,
	"GERADORA"	TEXT,
	"PROPRIETARIO"	TEXT,
	"NOME"	TEXT,
	"PLANILHA"	TEXT,
	"URL_DASHBOARD"	TEXT,
	"CRITERIO_PROC"	TEXT,
	"DESC_GERAR"	BLOB,
	"RECEBE_ENERGIA_DE"	TEXT,
	"VALOR_ALUGUEL"	REAL,
	"PATH_FATURA"	TEXT,
	PRIMARY KEY("UNIDADE_EDP")
);
INSERT INTO "nomes" VALUES('1793752','0','Adilson','Adilson 1793752',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160508005','0','Adilson','Adilson 160508005',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160400900','0','Cubinhos','Cubinhos 160400900',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('318923','0','Lupe','Lupe 318923',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160703715','0','Auto Posto Pedra Azul LTDA','Auto Posto Pedra Azul LTDA 160703715',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('1577188','0','Auto Posto Pedra Azul LTDA','Auto Posto Pedra Azul LTDA 1577188',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161086526','0','Terrazzo Dei Nonni LTDA','Terrazzo Dei Nonni LTDA 161086526',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161086525','0','Emporio Dei Nonni LTDA','Emporio Dei Nonni LTDA 161086525',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160523291','0','Curbani e CIA LTDA','Curbani e CIA LTDA 160523291',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('1989890','0','Loja Curbani','Loja Curbani 1989890',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('1897967','0','Loja Curbani','Loja Curbani 1897967',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('503047','0','Maria da Penha Fazolo Curbani','Maria da Penha Fazolo Curbani 503047',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('226705','0','Restaurante Don Due LTDA','Restaurante Don Due LTDA 226705',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160800912','0','Vallino P. Napoletana LTDA','Vallino P. Napoletana LTDA 160800912',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('1043813','0','Fredelino','Fredelino 1043813',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160993441','1','ULT','ULT 1',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161084053','1','ULT','ULT 2',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161041889','1','ULT','ULT 3',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161041895','1','ULT','ULT 4',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161099718','1','Lucas Generoso','LUCAS GENEROSO 1',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161147185','1','Gilles','Gilles 1',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161127416','1','DCN','GD3 - MAIS ALIMENTOS',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161171784','1','Poleto','POLETO 1',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('45841','0','Adilson','Adilson 45841',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('1392132','0','Juruceia','Juruceia 1392132',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('247719','0','Luciana Canal','Luciana Canal 247719',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('731657','0','Luciana Canal','Luciana Canal 731657',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('160580238','0','Luciana Canal','Luciana Canal 160580238',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('161078685','0','Diego','Diego 161078685',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
INSERT INTO "nomes" VALUES('766696','0','Ayrton','Ayrton 766696',NULL,NULL,NULL,'FALSE',NULL,NULL,'/media/hdfs/ULT/16 - Nova apuracao/');
COMMIT;
