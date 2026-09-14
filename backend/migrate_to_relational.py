import asyncio
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine, Base
from app.models.db_models import Product, Standard, ProductStandard, KnowledgeChunk
from app.services.vector_service import get_vector_service

# Create new tables in SQLite
print("Creating tables in database...")
Base.metadata.create_all(bind=engine)

def migrate_qdrant_to_db():
    print("Starting migration from Qdrant to SQLite...")
    db: Session = SessionLocal()
    try:
        vs = get_vector_service()
        
        # Scroll through all points in Qdrant
        response = vs._client.scroll(
            collection_name="bis_standards_v2",
            limit=1000, # Assuming we have <1000 chunks based on previous 353 count
            with_payload=True
        )
        
        points = response[0]
        print(f"Found {len(points)} chunks in Qdrant.")
        
        # Keep track of created standards to avoid duplicates
        standard_cache = {}
        
        # We'll create a default "LED Lamp" product for demoing the join query
        led_product = db.query(Product).filter_by(product_name="LED Lamp").first()
        if not led_product:
            led_product = Product(product_name="LED Lamp")
            db.add(led_product)
            db.commit()
            
        for point in points:
            payload = point.payload
            
            # 1. Handle Standard
            # Sometimes payload['standard_code'] is 'N/A' or missing. We'll fallback to source_file.
            is_number = payload.get('standard_code')
            source_file = payload.get('source_file', 'unknown.pdf')
            
            if not is_number or is_number == 'N/A':
                is_number = source_file.replace('.pdf', '').replace('_', ' ')
                
            if is_number not in standard_cache:
                standard = db.query(Standard).filter_by(is_number=is_number).first()
                if not standard:
                    standard = Standard(
                        is_number=is_number,
                        title=source_file # Use source file as a rough title for now
                    )
                    db.add(standard)
                    db.commit()
                    db.refresh(standard)
                    
                    # Link to LED Lamp if the standard mentions LED
                    if "LED" in is_number.upper() or "LED" in source_file.upper():
                        ps = ProductStandard(
                            product_id=led_product.product_id,
                            standard_id=standard.standard_id,
                            relationship_type="Product Standard"
                        )
                        db.add(ps)
                        db.commit()
                        
                standard_cache[is_number] = standard
                
            standard = standard_cache[is_number]
            
            # 2. Handle Chunk
            chunk_id = str(point.id)
            
            # Ensure it doesn't already exist
            existing_chunk = db.query(KnowledgeChunk).filter_by(chunk_id=chunk_id).first()
            if not existing_chunk:
                clause = payload.get('clause_number')
                # For page number, we don't have it in the PDF extraction currently, so we'll leave it null or fake it
                
                chunk = KnowledgeChunk(
                    chunk_id=chunk_id,
                    standard_id=standard.standard_id,
                    clause_number=clause,
                    text=payload.get('text', '')
                )
                db.add(chunk)
                
        db.commit()
        print("Migration complete! Data successfully inserted into structured SQL tables.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_qdrant_to_db()
