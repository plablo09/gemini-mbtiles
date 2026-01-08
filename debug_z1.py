import duckdb

def check_z0():
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL spatial; LOAD spatial;")
    
    # z=0, x=0, y=0
    # XYZ: The whole world (usually). Or Top-Left quadrant if it's not the whole world.
    # Actually at z=0, x=0,y=0 covers the whole world in Web Mercator.
    
    # Let's check z=1.
    # z=1, x=0, y=0.
    # XYZ: North-West quadrant. (Lon -180 to 0, Lat 0 to 85.05)
    # TMS: South-West quadrant. (Lon -180 to 0, Lat -85.05 to 0)
    
    print("Checking z=1, x=0, y=0")
    env = con.execute("SELECT ST_AsText(ST_TileEnvelope(1, 0, 0))").fetchone()[0]
    box = con.execute("SELECT ST_Extent(ST_TileEnvelope(1, 0, 0))").fetchone()[0]
    print(f"Env: {env}")
    print(f"Box: {box}")

if __name__ == "__main__":
    check_z0()
