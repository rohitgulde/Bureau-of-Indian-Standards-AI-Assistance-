from app.database.session import SessionLocal
from app.models.db_models import Product, Standard, ProductStandard
from app.routers.ingest import _infer_category

def fix_database():
    db = SessionLocal()
    
    standards = db.query(Standard).all()
    print(f"Found {len(standards)} standards in the database.")
    
    for standard in standards:
        # We need the filename to pass to _infer_category for intelligent fallback
        filename = standard.title or ""
        
        # If it's the junk 'hello' standard, skip it
        if standard.is_number == "hello":
            continue
            
        # Infer the correct product category
        prod_cat_name = _infer_category(standard.is_number, filename)
        
        if not prod_cat_name or prod_cat_name == "Unknown":
            prod_cat_name = "General Product"
            
        print(f"Standard '{standard.is_number}' -> Mapping to: '{prod_cat_name}'")
        
        # Update the product associated with this standard
        ps_links = db.query(ProductStandard).filter_by(standard_id=standard.standard_id).all()
        for ps in ps_links:
            product = db.query(Product).filter_by(product_id=ps.product_id).first()
            if product:
                # If the product name is the old raw IS number or "General Product", rename it
                if product.product_name == standard.is_number or product.product_name == "General Product":
                    print(f"  [+] Renaming product '{product.product_name}' -> '{prod_cat_name}'")
                    product.product_name = prod_cat_name
                    db.commit()

    # Consolidate duplicate products if any exist after renaming
    products = db.query(Product).all()
    product_map = {}
    for p in products:
        if p.product_name not in product_map:
            product_map[p.product_name] = p
        else:
            # We found a duplicate, migrate its links to the primary one and delete
            primary = product_map[p.product_name]
            links = db.query(ProductStandard).filter_by(product_id=p.product_id).all()
            for link in links:
                # check if primary already has this link
                existing = db.query(ProductStandard).filter_by(product_id=primary.product_id, standard_id=link.standard_id).first()
                if not existing:
                    link.product_id = primary.product_id
                else:
                    db.delete(link)
            db.commit()
            print(f"  [+] Removed duplicate product entry for '{p.product_name}'")
            db.delete(p)
            db.commit()

    # Remove the junk "hello" standard and product if it exists
    hello_std = db.query(Standard).filter_by(is_number="hello").first()
    if hello_std:
        links = db.query(ProductStandard).filter_by(standard_id=hello_std.standard_id).all()
        for l in links:
            db.delete(l)
        db.delete(hello_std)
        db.commit()
        
    hello_prod = db.query(Product).filter_by(product_name="hello").first()
    if hello_prod:
        db.delete(hello_prod)
        db.commit()
        print("  [+] Deleted junk 'hello' data.")

    db.close()
    print("Database fix complete!")

if __name__ == "__main__":
    fix_database()
