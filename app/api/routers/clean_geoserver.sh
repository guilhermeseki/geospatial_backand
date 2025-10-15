#file format: chirps_final_latam_20250703.tif 
#1 First, let's check your existing indexer.properties:

cat /opt/geoserver/data_dir/chirps_final/indexer.properties

# #2. Let's create the proper configuration files:
# sudo tee /opt/geoserver/data_dir/chirps_final/indexer.properties > /dev/null << 'EOF'
# Indexer.source=granules
# Indexer.suffix=.tif
# TimeAttribute=time
# Schema=*the_geom:Polygon,location:String,time:java.util.Date
# PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](time)
# Recursive=true
# EOF

sudo tee /opt/geospatial_backend/data/chirps_final/indexer.properties > /dev/null << 'EOF'
# indexer.properties
Schema=*the_geom:Polygon,location:String,timestamp:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](timestamp)
TimeAttribute=timestamp
EOF

# sudo tee /usr/share/geoserver-2.27.2/geoserver-data/test_mosaic/timeregex.properties > /dev/null << 'EOF'
# regex=.*_(\d{8})\.tif
# format=yyyyMMdd
# EOF

sudo tee /opt/geospatial_backend/data/chirps_final/timeregex.properties > /dev/null << 'EOF'
regex=chirps_final_latam_([0-9]{8})\.tif
property=time
EOF

#Create datastore.properties:

sudo tee /opt/geospatial_backend/data/chirps_final/datastore.properties > /dev/null << 'EOF'
type=ImageMosaic

EOF


cd /opt/geospatial_backend/data/chirps_final
java -cp "$GEOSERVER_HOME/webapps/geoserver/WEB-INF/lib/*" \
     org.geotools.coverage.io.imagemosaic.Utils \
     -p indexer.properties \
     -o .

sudo chown -R guilherme:guilherme /opt/geospatial_backend/data/chirps_final
sudo chmod -R 755 /opt/geospatial_backend/data/chirps_final

# 1. Delete the layer (optional if recurse is used on coverage store)
curl -u admin:geoserver -X DELETE \
"http://localhost:8080/geoserver/rest/layers/chirps_final?recurse=true"

# 2. Delete the coverage (recursively)
curl -u admin:geoserver -X DELETE \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages/chirps_final?recurse=true"

# 3. Delete the coverage store (recursively)
curl -u admin:geoserver -X DELETE \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic?recurse=true"

# 4. Delete the workspace (recursively)
curl -u admin:geoserver -X DELETE \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws?recurse=true"

# Wait a few seconds, then verify deletion
sleep 2
curl -u admin:geoserver "http://localhost:8080/geoserver/rest/workspaces"

#recreate
curl -u admin:geoserver -X POST \
  -H "Content-Type: text/xml" \
  -d "<workspace><name>precipitation_ws</name></workspace>" \
  "http://localhost:8080/geoserver/rest/workspaces"

#3. Now let's force GeoServer to reload the mosaic by recreating the coverage store:


# Create coverage store
curl -u admin:geoserver -X POST \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores" \
-H "Content-Type: text/xml" \
-d "<coverageStore>
      <name>chirps_final</name>
      <type>ImageMosaic</type>
      <enabled>true</enabled>
      <workspace>precipitation_ws</workspace>
      <url>file:/opt/geoserver/data_dir/chirps_final</url>
    </coverageStore>"

#this workid intead the command above
curl -u admin:geoserver -X POST -H "Content-type: text/xml" \
-d "<coverageStore>
      <name>chirps_final</name>
      <workspace>precipitation_ws</workspace>
      <enabled>true</enabled>
      <type>ImageMosaic</type>
      <url>file:///opt/geospatial_backend/data/chirps_final</url>
    </coverageStore>" \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores"

#check if the coverage store was created
curl -u admin:geoserver \
     -XGET "http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores.json"


#publish a coverage (layer) from that store
curl -u admin:geoserver -X POST \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages" \
-H "Content-Type: text/xml" \
-d "<coverage>
      <name>chirps_final</name>
      <title>CHIRPS Daily Precipitation</title>
      <description>Daily precipitation data from CHIRPS</description>
      <enabled>true</enabled>
      <srs>EPSG:4326</srs>
      <projectionPolicy>FORCE_DECLARED</projectionPolicy>
    </coverage>"


#2. Let's manually create the coverage with time enabled:#

curl -u admin:geoserver -X POST \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages" \
-H "Content-Type: text/xml" \
-d "<coverage>
      <name>chirps_final</name>
      <title>CHIRPS Daily Precipitation</title>
      <description>Daily precipitation data from CHIRPS</description>
      <enabled>true</enabled>
      <metadata>
        <entry key="time">
          <dimensionInfo>
            <enabled>true</enabled>
            <presentation>LIST</presentation>
            <resolution>86400000</resolution>
            <defaultValue>
              <strategy>MAXIMUM</strategy>
            </defaultValue>
          </dimensionInfo>
        </entry>
      </metadata>
      <srs>EPSG:4326</srs>
      <projectionPolicy>FORCE_DECLARED</projectionPolicy>
    </coverage>"

#Let's verify the coverage was created:

# Check if the coverage now exists

curl -u admin:geoserver \
     -XGET "http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages.json"

#list all coverage in worksapce
curl -u admin:geoserver \
     -XGET "http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages.json"

# Get detailed information about the coverage
curl -u admin:geoserver -X GET \
"http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps_final_mosaic/coverages/chirps_final.xml"

#verify time
ogrinfo -al /opt/geospatial_backend/data/chirps_final/chirps_final.shp