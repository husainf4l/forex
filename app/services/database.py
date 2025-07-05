"""
Database service for storing and retrieving gold market data
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncpg
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """Database service for gold market data"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        if self._initialized:
            return

        logger.info("🚀 Initializing database service...")

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=settings.DATABASE_HOST,
                port=settings.DATABASE_PORT,
                user=settings.DATABASE_USER,
                password=settings.DATABASE_PASSWORD,
                database=settings.DATABASE_NAME,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            logger.info("✅ Database connection established successfully")

            # Initialize tables
            await self._initialize_tables()

            self._initialized = True
            logger.info("✅ Database service initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup database connections"""
        if self.pool:
            await self.pool.close()
            self.pool = None
        self._initialized = False
        logger.info("✅ Database service cleanup completed")

    async def _initialize_tables(self) -> None:
        """Initialize database tables"""
        logger.info("🔧 Setting up database tables...")

        # Drop existing tables (be careful in production!)
        drop_tables_sql = """
        DROP TABLE IF EXISTS gold_prices_minute CASCADE;
        DROP TABLE IF EXISTS gold_prices_hour CASCADE;
        DROP TABLE IF EXISTS gold_prices_daily CASCADE;
        DROP TABLE IF EXISTS data_fetch_log CASCADE;
        """

        # Create tables
        create_tables_sql = """
        -- Table for minute-by-minute gold prices
        CREATE TABLE gold_prices_minute (
            id SERIAL PRIMARY KEY,
            epic VARCHAR(50) NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            snapshot_time_utc TIMESTAMP NOT NULL,
            open_bid DECIMAL(10,2) NOT NULL,
            open_ask DECIMAL(10,2) NOT NULL,
            close_bid DECIMAL(10,2) NOT NULL,
            close_ask DECIMAL(10,2) NOT NULL,
            high_bid DECIMAL(10,2) NOT NULL,
            high_ask DECIMAL(10,2) NOT NULL,
            low_bid DECIMAL(10,2) NOT NULL,
            low_ask DECIMAL(10,2) NOT NULL,
            volume BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(epic, snapshot_time_utc)
        );

        -- Table for hourly gold prices (aggregated)
        CREATE TABLE gold_prices_hour (
            id SERIAL PRIMARY KEY,
            epic VARCHAR(50) NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            snapshot_time_utc TIMESTAMP NOT NULL,
            open_bid DECIMAL(10,2) NOT NULL,
            open_ask DECIMAL(10,2) NOT NULL,
            close_bid DECIMAL(10,2) NOT NULL,
            close_ask DECIMAL(10,2) NOT NULL,
            high_bid DECIMAL(10,2) NOT NULL,
            high_ask DECIMAL(10,2) NOT NULL,
            low_bid DECIMAL(10,2) NOT NULL,
            low_ask DECIMAL(10,2) NOT NULL,
            volume BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(epic, snapshot_time_utc)
        );

        -- Table for daily gold prices (aggregated)
        CREATE TABLE gold_prices_daily (
            id SERIAL PRIMARY KEY,
            epic VARCHAR(50) NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            snapshot_time_utc TIMESTAMP NOT NULL,
            open_bid DECIMAL(10,2) NOT NULL,
            open_ask DECIMAL(10,2) NOT NULL,
            close_bid DECIMAL(10,2) NOT NULL,
            close_ask DECIMAL(10,2) NOT NULL,
            high_bid DECIMAL(10,2) NOT NULL,
            high_ask DECIMAL(10,2) NOT NULL,
            low_bid DECIMAL(10,2) NOT NULL,
            low_ask DECIMAL(10,2) NOT NULL,
            volume BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(epic, snapshot_time_utc)
        );

        -- Table for tracking data fetch operations
        CREATE TABLE data_fetch_log (
            id SERIAL PRIMARY KEY,
            epic VARCHAR(50) NOT NULL,
            resolution VARCHAR(20) NOT NULL,
            from_date TIMESTAMP NOT NULL,
            to_date TIMESTAMP NOT NULL,
            records_fetched INTEGER DEFAULT 0,
            records_inserted INTEGER DEFAULT 0,
            fetch_duration_seconds INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'started',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for better performance
        CREATE INDEX idx_gold_prices_minute_time ON gold_prices_minute(snapshot_time_utc);
        CREATE INDEX idx_gold_prices_minute_epic ON gold_prices_minute(epic);
        CREATE INDEX idx_gold_prices_hour_time ON gold_prices_hour(snapshot_time_utc);
        CREATE INDEX idx_gold_prices_hour_epic ON gold_prices_hour(epic);
        CREATE INDEX idx_gold_prices_daily_time ON gold_prices_daily(snapshot_time_utc);
        CREATE INDEX idx_gold_prices_daily_epic ON gold_prices_daily(epic);
        CREATE INDEX idx_data_fetch_log_time ON data_fetch_log(created_at);
        """

        async with self.pool.acquire() as conn:
            # Drop existing tables
            await conn.execute(drop_tables_sql)
            logger.info("🗑️ Existing tables dropped")

            # Create new tables
            await conn.execute(create_tables_sql)
            logger.info("✅ Database tables created successfully")

    async def insert_minute_prices(
        self, epic: str, price_data: List[Dict[str, Any]]
    ) -> int:
        """
        Insert minute-by-minute price data into the database

        Args:
            epic: Market epic (e.g., 'GOLD')
            price_data: List of price records from API

        Returns:
            Number of records inserted
        """
        if not price_data:
            return 0

        logger.info(f"💾 Inserting {len(price_data)} minute price records for {epic}")

        insert_sql = """
        INSERT INTO gold_prices_minute (
            epic, snapshot_time, snapshot_time_utc,
            open_bid, open_ask, close_bid, close_ask,
            high_bid, high_ask, low_bid, low_ask, volume
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (epic, snapshot_time_utc) DO UPDATE SET
            open_bid = EXCLUDED.open_bid,
            open_ask = EXCLUDED.open_ask,
            close_bid = EXCLUDED.close_bid,
            close_ask = EXCLUDED.close_ask,
            high_bid = EXCLUDED.high_bid,
            high_ask = EXCLUDED.high_ask,
            low_bid = EXCLUDED.low_bid,
            low_ask = EXCLUDED.low_ask,
            volume = EXCLUDED.volume
        """

        inserted_count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for record in price_data:
                    try:
                        # Parse timestamps
                        snapshot_time = datetime.fromisoformat(
                            record["snapshotTime"].replace("Z", "+00:00")
                        )
                        snapshot_time_utc = datetime.fromisoformat(
                            record["snapshotTimeUTC"].replace("Z", "+00:00")
                        )

                        # Execute insert
                        await conn.execute(
                            insert_sql,
                            epic,
                            snapshot_time,
                            snapshot_time_utc,
                            float(record["openPrice"]["bid"]),
                            float(record["openPrice"]["ask"]),
                            float(record["closePrice"]["bid"]),
                            float(record["closePrice"]["ask"]),
                            float(record["highPrice"]["bid"]),
                            float(record["highPrice"]["ask"]),
                            float(record["lowPrice"]["bid"]),
                            float(record["lowPrice"]["ask"]),
                            int(record.get("lastTradedVolume", 0)),
                        )
                        inserted_count += 1

                    except Exception as e:
                        logger.error(f"❌ Error inserting record: {e}")
                        logger.error(f"Record: {record}")
                        continue

        logger.info(f"✅ Successfully inserted {inserted_count} minute price records")
        return inserted_count

    async def insert_hour_prices(
        self, epic: str, price_data: List[Dict[str, Any]]
    ) -> int:
        """Insert hourly price data into the database"""
        if not price_data:
            return 0

        logger.info(f"💾 Inserting {len(price_data)} hourly price records for {epic}")

        insert_sql = """
        INSERT INTO gold_prices_hour (
            epic, snapshot_time, snapshot_time_utc,
            open_bid, open_ask, close_bid, close_ask,
            high_bid, high_ask, low_bid, low_ask, volume
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (epic, snapshot_time_utc) DO UPDATE SET
            open_bid = EXCLUDED.open_bid,
            open_ask = EXCLUDED.open_ask,
            close_bid = EXCLUDED.close_bid,
            close_ask = EXCLUDED.close_ask,
            high_bid = EXCLUDED.high_bid,
            high_ask = EXCLUDED.high_ask,
            low_bid = EXCLUDED.low_bid,
            low_ask = EXCLUDED.low_ask,
            volume = EXCLUDED.volume
        """

        inserted_count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for record in price_data:
                    try:
                        # Parse timestamps
                        snapshot_time = datetime.fromisoformat(
                            record["snapshotTime"].replace("Z", "+00:00")
                        )
                        snapshot_time_utc = datetime.fromisoformat(
                            record["snapshotTimeUTC"].replace("Z", "+00:00")
                        )

                        # Execute insert
                        await conn.execute(
                            insert_sql,
                            epic,
                            snapshot_time,
                            snapshot_time_utc,
                            float(record["openPrice"]["bid"]),
                            float(record["openPrice"]["ask"]),
                            float(record["closePrice"]["bid"]),
                            float(record["closePrice"]["ask"]),
                            float(record["highPrice"]["bid"]),
                            float(record["highPrice"]["ask"]),
                            float(record["lowPrice"]["bid"]),
                            float(record["lowPrice"]["ask"]),
                            int(record.get("lastTradedVolume", 0)),
                        )
                        inserted_count += 1

                    except Exception as e:
                        logger.error(f"❌ Error inserting record: {e}")
                        continue

        logger.info(f"✅ Successfully inserted {inserted_count} hourly price records")
        return inserted_count

    async def log_fetch_operation(
        self,
        epic: str,
        resolution: str,
        from_date: datetime,
        to_date: datetime,
        records_fetched: int = 0,
        records_inserted: int = 0,
        duration_seconds: int = 0,
        status: str = "completed",
        error_message: str = None,
    ) -> int:
        """Log a data fetch operation"""

        insert_sql = """
        INSERT INTO data_fetch_log (
            epic, resolution, from_date, to_date, records_fetched, 
            records_inserted, fetch_duration_seconds, status, error_message
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                insert_sql,
                epic,
                resolution,
                from_date,
                to_date,
                records_fetched,
                records_inserted,
                duration_seconds,
                status,
                error_message,
            )
            return row["id"]

    async def get_latest_price_date(
        self, epic: str, resolution: str = "MINUTE"
    ) -> Optional[datetime]:
        """Get the latest price date for a given epic and resolution"""

        table_name = f"gold_prices_{resolution.lower()}"

        query = f"""
        SELECT MAX(snapshot_time_utc) as latest_date
        FROM {table_name}
        WHERE epic = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, epic)
            return row["latest_date"] if row else None

    async def get_price_data(
        self,
        epic: str,
        resolution: str = "MINUTE",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get price data from database"""

        table_name = f"gold_prices_{resolution.lower()}"

        query = f"""
        SELECT * FROM {table_name}
        WHERE epic = $1
        """

        params = [epic]

        if from_date:
            query += " AND snapshot_time_utc >= $2"
            params.append(from_date)

        if to_date:
            query += f" AND snapshot_time_utc <= ${len(params) + 1}"
            params.append(to_date)

        query += " ORDER BY snapshot_time_utc DESC"
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""

        stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM gold_prices_minute) as minute_records,
            (SELECT COUNT(*) FROM gold_prices_hour) as hour_records,
            (SELECT COUNT(*) FROM gold_prices_daily) as daily_records,
            (SELECT MIN(snapshot_time_utc) FROM gold_prices_minute) as earliest_minute,
            (SELECT MAX(snapshot_time_utc) FROM gold_prices_minute) as latest_minute,
            (SELECT MIN(snapshot_time_utc) FROM gold_prices_hour) as earliest_hour,
            (SELECT MAX(snapshot_time_utc) FROM gold_prices_hour) as latest_hour
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(stats_query)
            return dict(row)

    async def store_minute_prices(self, processed_data: List[Dict[str, Any]]) -> int:
        """
        Store minute price data that has been processed by the data fetcher

        Args:
            processed_data: List of processed price records from GoldDataFetcher

        Returns:
            Number of records stored
        """
        if not processed_data:
            return 0

        logger.info(f"💾 Storing {len(processed_data)} processed minute price records")

        insert_sql = """
        INSERT INTO gold_prices_minute (
            epic, snapshot_time, snapshot_time_utc,
            open_bid, open_ask, close_bid, close_ask,
            high_bid, high_ask, low_bid, low_ask, volume
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (epic, snapshot_time_utc) DO UPDATE SET
            open_bid = EXCLUDED.open_bid,
            open_ask = EXCLUDED.open_ask,
            close_bid = EXCLUDED.close_bid,
            close_ask = EXCLUDED.close_ask,
            high_bid = EXCLUDED.high_bid,
            high_ask = EXCLUDED.high_ask,
            low_bid = EXCLUDED.low_bid,
            low_ask = EXCLUDED.low_ask,
            volume = EXCLUDED.volume
        """

        stored_count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for record in processed_data:
                    try:
                        # Extract data from processed record
                        epic = record.get("epic", "GOLD")
                        timestamp = record.get("timestamp")

                        # Convert timestamp to UTC if needed
                        if isinstance(timestamp, datetime):
                            snapshot_time_utc = timestamp.replace(tzinfo=None)
                        else:
                            snapshot_time_utc = datetime.fromisoformat(
                                str(timestamp).replace("Z", "")
                            )

                        # Use the same time for both fields
                        snapshot_time = snapshot_time_utc

                        # Execute insert
                        await conn.execute(
                            insert_sql,
                            epic,
                            snapshot_time,
                            snapshot_time_utc,
                            float(record.get("open_bid", 0)),
                            float(record.get("open_ask", 0)),
                            float(record.get("close_bid", 0)),
                            float(record.get("close_ask", 0)),
                            float(record.get("high_bid", 0)),
                            float(record.get("high_ask", 0)),
                            float(record.get("low_bid", 0)),
                            float(record.get("low_ask", 0)),
                            int(record.get("volume", 0) or 0),
                        )
                        stored_count += 1

                    except Exception as e:
                        logger.error(f"❌ Error storing record: {e}")
                        logger.error(f"Record: {record}")
                        continue

        logger.info(f"✅ Successfully stored {stored_count} minute price records")
        return stored_count

    async def get_data_statistics(self) -> Dict[str, Any]:
        """Get comprehensive data statistics"""

        stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM gold_prices_minute) as total_records,
            (SELECT COUNT(*) FROM gold_prices_minute) as minute_records,
            (SELECT COUNT(*) FROM gold_prices_hour) as hour_records,
            (SELECT COUNT(*) FROM gold_prices_daily) as daily_records,
            (SELECT MIN(snapshot_time_utc) FROM gold_prices_minute) as min_date,
            (SELECT MAX(snapshot_time_utc) FROM gold_prices_minute) as max_date,
            (SELECT pg_size_pretty(pg_total_relation_size('gold_prices_minute'))) as database_size
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(stats_query)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"❌ Error getting data statistics: {e}")
            return {}

    @property
    def is_initialized(self) -> bool:
        """Check if database service is initialized"""
        return self._initialized and self.pool is not None
