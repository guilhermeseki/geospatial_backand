<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>precipitation_style</Name>
    <UserStyle>
      <Title>Precipitation Style</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry color="#0000FF" quantity="0" label="No Data" opacity="0"/>
              <ColorMapEntry color="#9ECAE1" quantity="10" label="Very Low"/>
              <ColorMapEntry color="#6BAED6" quantity="50" label="Low"/>
              <ColorMapEntry color="#4292C6" quantity="100" label="Moderate"/>
              <ColorMapEntry color="#2171B5" quantity="150" label="High"/>
              <ColorMapEntry color="#08306B" quantity="200" label="Very High"/>
              <ColorMapEntry color="#FF0000" quantity="300" label="Extreme"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
