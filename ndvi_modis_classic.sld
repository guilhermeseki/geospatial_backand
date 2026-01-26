<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>MODIS NDVI Classic</Name>
    <UserStyle>
      <Title>MODIS NDVI Classic Style (GeoServer Standard)</Title>
      <Abstract>
        Classic NDVI color ramp for 0-1 range.
        Red = No/Low vegetation, Yellow = Moderate, Green = Dense.
      </Abstract>
      <FeatureTypeStyle>
        <Rule>
          <Name>NDVI Classic</Name>
          <Title>NDVI Classic</Title>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- No data -->
              <ColorMapEntry color="#000000" quantity="0" label="No Data" opacity="0"/>

              <!-- Low vegetation -->
              <ColorMapEntry color="#FF0000" quantity="0.1" label="Very sparse"/>
              <ColorMapEntry color="#FF8800" quantity="0.2" label="Sparse"/>

              <!-- Moderate vegetation -->
              <ColorMapEntry color="#FFFF00" quantity="0.4" label="Moderate low"/>
              <ColorMapEntry color="#AAFF00" quantity="0.6" label="Moderate"/>

              <!-- Dense vegetation -->
              <ColorMapEntry color="#00FF00" quantity="0.8" label="Healthy"/>
              <ColorMapEntry color="#006600" quantity="1.0" label="Dense"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
