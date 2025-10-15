<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>precipitation_style</Name>
    <UserStyle>
      <Title>Precipitation Style - Custom Colorbar</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>

              <!-- boundaries & colors -->
              <ColorMapEntry color="#FFFFFF" quantity="0" label="0" opacity="0"/> <!-- white -->
              <ColorMapEntry color="#50D0D0" quantity="1" label="1"/> <!-- (0.3137,0.8157,0.8157) -->
              <ColorMapEntry color="#00FFFF" quantity="2.5" label="2.5"/> <!-- cyan -->
              <ColorMapEntry color="#00E080" quantity="5" label="5"/> <!-- (0,0.878,0.502) -->
              <ColorMapEntry color="#00C000" quantity="7.5" label="7.5"/> <!-- green -->
              <ColorMapEntry color="#CCE000" quantity="10" label="10"/> <!-- yellow-green -->
              <ColorMapEntry color="#FFFF00" quantity="15" label="15"/> <!-- yellow -->
              <ColorMapEntry color="#FFA000" quantity="20" label="20"/> <!-- orange -->
              <ColorMapEntry color="#FF0000" quantity="30" label="30"/> <!-- red -->
              <ColorMapEntry color="#FF2080" quantity="40" label="40"/> <!-- pinkish -->
              <ColorMapEntry color="#F041FF" quantity="50" label="50"/> <!-- violet -->
              <ColorMapEntry color="#8020FF" quantity="70" label="70"/> <!-- purple -->
              <ColorMapEntry color="#4040FF" quantity="100" label="100"/> <!-- blue -->
              <ColorMapEntry color="#202080" quantity="150" label="150"/> <!-- dark blue -->
              <ColorMapEntry color="#202020" quantity="200" label="200"/> <!-- dark gray -->
              <ColorMapEntry color="#808080" quantity="250" label="250"/> <!-- gray -->
              <ColorMapEntry color="#E0E0E0" quantity="300" label="300"/> <!-- light gray -->
              <ColorMapEntry color="#EED4BC" quantity="400" label="400"/> <!-- beige -->
              <ColorMapEntry color="#DAA675" quantity="500" label="500"/> <!-- brown -->
              <ColorMapEntry color="#A06C3C" quantity="600" label="600"/> <!-- dark brown -->
              <ColorMapEntry color="#663300" quantity="750" label="750"/> <!-- very dark brown -->

            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>

