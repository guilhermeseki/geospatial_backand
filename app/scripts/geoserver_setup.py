indexer.properties

TimeAttribute=ingestion
Schema=*the_geom:Polygon,location:String,ingestion:java.sql.Timestamp
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion,yyyyMMdd)


regex=[0-9]{8}

