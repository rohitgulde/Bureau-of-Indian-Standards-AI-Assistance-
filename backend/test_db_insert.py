from app.database.session import SessionLocal
from app.models.db_models import Product, Standard, ProductStandard, KnowledgeChunk

db = SessionLocal()

source_file = "helmet standard.pdf"
is_number = "helmet standard"
prod_cat_name = "General Product"

try:
    standard = db.query(Standard).filter_by(is_number=is_number).first()
    if not standard:
        standard = Standard(is_number=is_number, title=source_file)
        db.add(standard)
        db.commit()
        db.refresh(standard)
        
    product_record = db.query(Product).filter_by(product_name=prod_cat_name).first()
    if not product_record:
        product_record = Product(product_name=prod_cat_name)
        db.add(product_record)
        db.commit()
        db.refresh(product_record)
        
    existing_ps = db.query(ProductStandard).filter_by(
        product_id=product_record.product_id,
        standard_id=standard.standard_id
    ).first()
    
    if not existing_ps:
        ps = ProductStandard(
            product_id=product_record.product_id,
            standard_id=standard.standard_id,
            relationship_type="Product Standard"
        )
        db.add(ps)
        db.commit()

    print("Success")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
