<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>wind_speed</Name>
    <UserStyle>
      <Title>Wind Speed - Intensity (m/s)</Title>
      <Abstract>Color ramp for wind speed from 0 m/s (calm) to 25+ m/s (very strong)</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- Calm to light breeze: White to Light Blue -->
              <ColorMapEntry color="#FFFFFF" quantity="0" label="Calm (0 m/s)" opacity="0"/>
              <ColorMapEntry color="#E6F2FF" quantity="0.5" label="Light Air" opacity="0.7"/>
              <ColorMapEntry color="#CCE5FF" quantity="1" label="Light Air (1 m/s)" opacity="0.8"/>

              <!-- Light breeze: Light Blue to Blue -->
              <ColorMapEntry color="#99CCFF" quantity="2" label="Light Breeze" opacity="0.85"/>
              <ColorMapEntry color="#66B3FF" quantity="3" label="Light Breeze" opacity="0.9"/>

              <!-- Gentle to moderate breeze: Blue to Green -->
              <ColorMapEntry color="#3399FF" quantity="4" label="Gentle Breeze" opacity="0.95"/>
              <ColorMapEntry color="#00BFFF" quantity="5" label="Gentle Breeze" opacity="1"/>
              <ColorMapEntry color="#00CED1" quantity="6" label="Moderate Breeze" opacity="1"/>

              <!-- Fresh breeze: Cyan to Yellow-Green -->
              <ColorMapEntry color="#00E5B8" quantity="7" label="Fresh Breeze" opacity="1"/>
              <ColorMapEntry color="#00FF9F" quantity="8" label="Fresh Breeze" opacity="1"/>
              <ColorMapEntry color="#7FFF00" quantity="9" label="Strong Breeze" opacity="1"/>

              <!-- Strong breeze to gale: Yellow to Orange -->
              <ColorMapEntry color="#ADFF2F" quantity="10" label="Strong Breeze" opacity="1"/>
              <ColorMapEntry color="#FFFF00" quantity="11" label="Near Gale" opacity="1"/>
              <ColorMapEntry color="#FFD700" quantity="12" label="Near Gale" opacity="1"/>
              <ColorMapEntry color="#FFAA00" quantity="13" label="Gale" opacity="1"/>

              <!-- Gale to strong gale: Orange to Red -->
              <ColorMapEntry color="#FF8800" quantity="15" label="Gale" opacity="1"/>
              <ColorMapEntry color="#FF6600" quantity="17" label="Strong Gale" opacity="1"/>
              <ColorMapEntry color="#FF4400" quantity="20" label="Storm" opacity="1"/>

              <!-- Storm to hurricane: Red to Dark Red -->
              <ColorMapEntry color="#FF0000" quantity="25" label="Violent Storm" opacity="1"/>
              <ColorMapEntry color="#CC0000" quantity="30" label="Hurricane" opacity="1"/>
              <ColorMapEntry color="#990000" quantity="35" label="Violent Hurricane" opacity="1"/>
              <ColorMapEntry color="#660000" quantity="40" label="Extreme" opacity="1"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
