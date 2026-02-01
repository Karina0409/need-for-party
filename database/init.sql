USE need_for_party;

-- 1. Исправление таблицы roles (если нужно)
IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('roles') AND name = 'name')
BEGIN
    ALTER TABLE roles ALTER COLUMN name NVARCHAR(255) NOT NULL;
END

-- 2. Добавление тестовых вечеринок
IF NOT EXISTS (SELECT 1 FROM parties WHERE name LIKE '%Новогодняя%')
BEGIN
    INSERT INTO parties (name, cost, location, start_party, create_party, count_seats, id_city)
    VALUES 
    ('Новогодняя ночь', 3500.00, 'Клуб "Ледниковый"', 
     DATEADD(day, 3, GETDATE()), DATEADD(day, -30, GETDATE()), 200, 1),
    
    ('Рождественский бал', 2800.00, 'Ресторан "Сибирь"',
     DATEADD(day, 10, GETDATE()), DATEADD(day, -20, GETDATE()), 150, 1),
    
    ('Зимний фестиваль', 2200.00, 'Бар "У камина"',
     DATEADD(day, 20, GETDATE()), GETDATE(), 100, 1);
END

-- 3. Добавление тестовых билетов
IF NOT EXISTS (SELECT 1 FROM tickets)
BEGIN
    -- Билеты для вечеринки 1
    DECLARE @i INT = 1;
    WHILE @i <= 85
    BEGIN
        INSERT INTO tickets (id_user, id_party, date_sale)
        VALUES (
            @i, 
            1, 
            DATEADD(day, -CAST(RAND() * 30 AS INT), GETDATE())
        );
        SET @i = @i + 1;
    END;
    
    -- Билеты для вечеринки 2
    SET @i = 1;
    WHILE @i <= 45
    BEGIN
        INSERT INTO tickets (id_user, id_party, date_sale)
        VALUES (@i + 100, 2, DATEADD(day, -CAST(RAND() * 20 AS INT), GETDATE()));
        SET @i = @i + 1;
    END;
END

-- 4. Добавление тестовых скидок
IF NOT EXISTS (SELECT 1 FROM discounts)
BEGIN
    INSERT INTO discounts (discount, id_user, id_party) VALUES
    (10, 1, 1), (15, 3, 1), (5, 5, 1), (20, 10, 1),
    (10, 101, 2), (15, 105, 2), (5, 110, 2);
END

-- 5. Добавление employees (администраторов)
IF NOT EXISTS (SELECT 1 FROM employees)
BEGIN
    INSERT INTO employees (surname, name, lastname, birth, id_role, username, password, mail, phone_number)
    VALUES
    ('Бахметьев', 'Дмитрий', 'Вадимович', '2005-05-29', 
     (SELECT ID FROM roles WHERE name = 'Админ'), 
     'baha.dv', 'X10777xffzxB0o4gsbkpvo7pM0NbOl6RCwotddrzvt0=', 
     'bahmetev168@gmail.com', '89138058861'),
    
    ('Надеждин', 'Роман', 'Дмитриевич', '2007-09-30',
     (SELECT ID FROM roles WHERE name = 'Админ'),
     'graph', 'mvFbM25qlhmShTffMLLmojdlafz51+dz7M7eZWBlKaA=',
     'romannad5@inbox.ru', '89234115464');
END

-- 6. Проверка структуры
SELECT 
    'roles' as table_name, COUNT(*) as record_count 
FROM roles
UNION ALL
SELECT 'parties', COUNT(*) FROM parties
UNION ALL
SELECT 'tickets', COUNT(*) FROM tickets
UNION ALL
SELECT 'discounts', COUNT(*) FROM discounts
UNION ALL
SELECT 'users', COUNT(*) FROM users;