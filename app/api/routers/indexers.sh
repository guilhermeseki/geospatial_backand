sudo tee /mnt/workwork/geoserver_data/merge/indexer.properties > /dev/null << 'EOF'
TimeAttribute=ingestion
Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)

EOF

sudo tee /mnt/workwork/geoserver_data/merge/timeregex.properties > /dev/null << 'EOF'
regex=.*([0-9]{8}).*
format=yyyyMMdd

EOF

# Set ownership to the user running GeoServer (replace 'geoserver' with actual user, e.g., 'tomcat')
sudo chown -R guilherme:guilherme /usr/share/geoserver-2.27.2/data_dir/data/chirps
sudo chmod -R 755 /usr/share/geoserver-2.27.2/data_dir/data/chirps