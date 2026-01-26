// Paleta de Cores - Densidade de Raios (Lightning)
// Unidade: flashes/km²/30min
// Fonte: GOES-16/19 GLM (Geostationary Lightning Mapper)

const lightningPalette = {
  // Escala principal de cores (0 - 1500+ flashes/km²/30min)
  colors: [
    { value: 0, hex: "#000000", rgb: [0, 0, 0], label: "Nenhuma", opacity: 0 },
    { value: 1, hex: "#1a0033", rgb: [26, 0, 51], label: "Muito Baixa", opacity: 0.3 },
    { value: 5, hex: "#330066", rgb: [51, 0, 102], label: "Baixa", opacity: 0.5 },
    { value: 10, hex: "#4d0099", rgb: [77, 0, 153], label: "Moderada Baixa", opacity: 0.7 },
    { value: 20, hex: "#6600cc", rgb: [102, 0, 204], label: "Moderada", opacity: 0.8 },
    { value: 50, hex: "#0000ff", rgb: [0, 0, 255], label: "Moderada Alta", opacity: 0.85 },
    { value: 100, hex: "#00ccff", rgb: [0, 204, 255], label: "Alta", opacity: 0.9 },
    { value: 200, hex: "#00ff99", rgb: [0, 255, 153], label: "Muito Alta", opacity: 0.95 },
    { value: 400, hex: "#ffff00", rgb: [255, 255, 0], label: "Intensa", opacity: 0.95 },
    { value: 800, hex: "#ff9900", rgb: [255, 153, 0], label: "Muito Intensa", opacity: 1.0 },
    { value: 1500, hex: "#ff0000", rgb: [255, 0, 0], label: "Extrema", opacity: 1.0 }
  ],

  // Categorias simplificadas para legendas
  categories: [
    {
      min: 0,
      max: 1,
      hex: "#000000",
      rgb: [0, 0, 0],
      label: "Sem Atividade",
      description: "0 flashes/km²"
    },
    {
      min: 1,
      max: 10,
      hex: "#330066",
      rgb: [51, 0, 102],
      label: "Atividade Baixa",
      description: "1-10 flashes/km²"
    },
    {
      min: 10,
      max: 50,
      hex: "#6600cc",
      rgb: [102, 0, 204],
      label: "Atividade Moderada",
      description: "10-50 flashes/km²"
    },
    {
      min: 50,
      max: 200,
      hex: "#00ccff",
      rgb: [0, 204, 255],
      label: "Atividade Alta",
      description: "50-200 flashes/km²"
    },
    {
      min: 200,
      max: 800,
      hex: "#ffff00",
      rgb: [255, 255, 0],
      label: "Atividade Intensa",
      description: "200-800 flashes/km²"
    },
    {
      min: 800,
      max: 1500,
      hex: "#ff9900",
      rgb: [255, 153, 0],
      label: "Atividade Muito Intensa",
      description: "800-1500 flashes/km²"
    },
    {
      min: 1500,
      max: Infinity,
      hex: "#ff0000",
      rgb: [255, 0, 0],
      label: "Atividade Extrema",
      description: ">1500 flashes/km²"
    }
  ],

  // Classificação de tempestades FED (Flash Extent Density)
  stormClassification: [
    {
      category: 0,
      fedRange: "0-0.1",
      hex: "#F0F0F0",
      rgb: [240, 240, 240],
      label: "Sem Atividade",
      description: "Ruído ou atividade isolada"
    },
    {
      category: 1,
      fedRange: "0.1-1",
      hex: "#90EE90",
      rgb: [144, 238, 144],
      label: "Tempestade Fraca",
      description: "Célula jovem, convecção inicial"
    },
    {
      category: 2,
      fedRange: "1-4",
      hex: "#FFD700",
      rgb: [255, 215, 0],
      label: "Tempestade Moderada",
      description: "Convecção madura, chuva intensa"
    },
    {
      category: 3,
      fedRange: "4-12",
      hex: "#FF7F00",
      rgb: [255, 127, 0],
      label: "Tempestade Forte",
      description: "Corrente ascendente forte, possível granizo"
    },
    {
      category: 4,
      fedRange: "12-30",
      hex: "#FF3300",
      rgb: [255, 51, 0],
      label: "Tempestade Muito Forte",
      description: "Estruturas organizadas, multicélulas"
    },
    {
      category: 5,
      fedRange: "30-60",
      hex: "#B22222",
      rgb: [178, 34, 34],
      label: "Tempestade Severa",
      description: "Sinal típico de tempestades severas"
    },
    {
      category: 6,
      fedRange: "60-100",
      hex: "#C71585",
      rgb: [199, 21, 133],
      label: "Supercélula Provável",
      description: "Corrente ascendente persistente e possível rotação"
    },
    {
      category: 7,
      fedRange: ">100",
      hex: "#6A0DAD",
      rgb: [106, 13, 173],
      label: "Sistema Explosivo / MCS Intenso",
      description: "Risco extremo"
    }
  ],

  // Metadados
  metadata: {
    unit: "flashes/km²/30min",
    title: "Densidade de Raios",
    description: "Densidade máxima de raios em qualquer janela de 30 minutos",
    source: "GOES-16/19 GLM",
    spatialResolution: "~3.23 km × 3.23 km",
    temporalResolution: "Máximo de 30 minutos"
  }
};

// Função auxiliar para obter a cor baseada no valor
function getLightningColor(value) {
  const colors = lightningPalette.colors;

  // Encontrar os dois pontos mais próximos para interpolação
  for (let i = 0; i < colors.length - 1; i++) {
    if (value >= colors[i].value && value <= colors[i + 1].value) {
      // Retorna a cor do ponto inferior (sem interpolação)
      // Para interpolação linear, implementar cálculo RGB
      return colors[i].hex;
    }
  }

  // Se o valor for maior que o máximo, retorna a última cor
  if (value > colors[colors.length - 1].value) {
    return colors[colors.length - 1].hex;
  }

  // Se o valor for menor que o mínimo, retorna a primeira cor
  return colors[0].hex;
}

// Função para obter categoria simplificada
function getLightningCategory(value) {
  const categories = lightningPalette.categories;

  for (let i = 0; i < categories.length; i++) {
    if (value >= categories[i].min && value < categories[i].max) {
      return categories[i];
    }
  }

  return categories[categories.length - 1];
}

// Função para obter classificação de tempestade
function getStormClassification(fedValue) {
  const classifications = lightningPalette.stormClassification;

  if (fedValue < 0.1) return classifications[0];
  if (fedValue < 1) return classifications[1];
  if (fedValue < 4) return classifications[2];
  if (fedValue < 12) return classifications[3];
  if (fedValue < 30) return classifications[4];
  if (fedValue < 60) return classifications[5];
  if (fedValue < 100) return classifications[6];
  return classifications[7];
}

// Exportar para uso em módulos
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    lightningPalette,
    getLightningColor,
    getLightningCategory,
    getStormClassification
  };
}

// Exportar para ES6 modules
export {
  lightningPalette,
  getLightningColor,
  getLightningCategory,
  getStormClassification
};
