<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>ndvi_modis</Name>
    <UserStyle>
      <Title>NDVI MODIS - Vegetation Index</Title>
      <Abstract>Color ramp for NDVI values from -1 (water/clouds) to 1 (dense vegetation)</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- Water and non-vegetation: Blue to Light Blue -->
              <ColorMapEntry color="#0000FF" quantity="-1" label="Water" opacity="1"/>
              <ColorMapEntry color="#4169E1" quantity="-0.5" label="Deep Water" opacity="1"/>
              <ColorMapEntry color="#87CEEB" quantity="-0.2" label="Shallow Water" opacity="1"/>

              <!-- Bare soil and sparse vegetation: Brown to Tan -->
              <ColorMapEntry color="#D2B48C" quantity="-0.1" label="Bare Soil" opacity="1"/>
              <ColorMapEntry color="#DEB887" quantity="0" label="Very Sparse" opacity="1"/>
              <ColorMapEntry color="#F5DEB3" quantity="0.1" label="Sparse" opacity="1"/>

              <!-- Low to moderate vegetation: Yellow to Light Green -->
              <ColorMapEntry color="#FFFF99" quantity="0.2" label="Low Vegetation" opacity="1"/>
              <ColorMapEntry color="#CCFF66" quantity="0.3" label="Moderate Vegetation" opacity="1"/>
              <ColorMapEntry color="#99FF33" quantity="0.4" label="Healthy Vegetation" opacity="1"/>

              <!-- Healthy vegetation: Green shades -->
              <ColorMapEntry color="#66CC00" quantity="0.5" label="Dense Vegetation" opacity="1"/>
              <ColorMapEntry color="#33AA00" quantity="0.6" label="Very Dense" opacity="1"/>
              <ColorMapEntry color="#228B22" quantity="0.7" label="Forest" opacity="1"/>

              <!-- Very dense vegetation: Dark Green -->
              <ColorMapEntry color="#006400" quantity="0.8" label="Dense Forest" opacity="1"/>
              <ColorMapEntry color="#004D00" quantity="0.9" label="Very Dense Forest" opacity="1"/>
              <ColorMapEntry color="#003300" quantity="1.0" label="Maximum" opacity="1"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
