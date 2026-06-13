-- Align DB column names with Pydantic model field names

ALTER TABLE parlamentarians RENAME COLUMN house TO casa;
ALTER TABLE parlamentarians RENAME COLUMN name TO nome;
ALTER TABLE parlamentarians RENAME COLUMN party TO partido;
ALTER TABLE parlamentarians RENAME COLUMN photo_url TO foto_url;

ALTER TABLE propositions RENAME COLUMN house TO casa;

ALTER TABLE expenses RENAME COLUMN parliamentarian_name TO parlamentar_nome;
ALTER TABLE expenses RENAME COLUMN category TO categoria;
ALTER TABLE expenses RENAME COLUMN supplier TO fornecedor;
ALTER TABLE expenses RENAME COLUMN document_number TO documento;
ALTER TABLE expenses RENAME COLUMN document_date TO data;
ALTER TABLE expenses RENAME COLUMN value TO valor;
