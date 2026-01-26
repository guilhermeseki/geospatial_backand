<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>MODIS NDVI</Name>
    <UserStyle>
      <Title>MODIS NDVI Color Ramp (Scientifically Accurate)</Title>
      <Abstract>
        NDVI color ramp optimized for vegetation health monitoring.
        Red = No/Low vegetation (0-0.2)
        Yellow/Orange = Sparse vegetation (0.2-0.4)
        Light Green = Moderate vegetation (0.4-0.6)
        Green = Healthy vegetation (0.6-0.8)
        Dark Green = Dense vegetation (0.8-1.0)
      </Abstract>
      <FeatureTypeStyle>
        <Rule>
          <Name>NDVI</Name>
          <Title>NDVI Color Ramp</Title>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- Water and bare soil -->
              <ColorMapEntry color="#0C0C0C" quantity="-1" label="No Data" opacity="0"/>
              <ColorMapEntry color="#A50026" quantity="0.0" label="Bare soil/Water"/>

              <!-- Very sparse vegetation -->
              <ColorMapEntry color="#D73027" quantity="0.1" label="Very sparse"/>
              <ColorMapEntry color="#F46D43" quantity="0.2" label="Sparse"/>

              <!-- Sparse to moderate vegetation -->
              <ColorMapEntry color="#FDAE61" quantity="0.3" label="Moderate low"/>
              <ColorMapEntry color="#FEE08B" quantity="0.4" label="Moderate"/>

              <!-- Moderate vegetation -->
              <ColorMapEntry color="#D9EF8B" quantity="0.5" label="Moderate high"/>
              <ColorMapEntry color="#A6D96A" quantity="0.6" label="Healthy"/>

              <!-- Healthy vegetation -->
              <ColorMapEntry color="#66BD63" quantity="0.7" label="Very healthy"/>
              <ColorMapEntry color="#1A9850" quantity="0.8" label="Dense"/>

              <!-- Dense vegetation (rainforest) -->
              <ColorMapEntry color="#006837" quantity="0.9" label="Very dense"/>
              <ColorMapEntry color="#004529" quantity="1.0" label="Maximum"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
