// Mock for lightweight-charts module
const createChart = jest.fn(() => ({
  addCandlestickSeries: jest.fn(() => ({
    setData: jest.fn(),
    update: jest.fn(),
    priceScale: jest.fn(() => ({
      applyOptions: jest.fn(),
    })),
    applyOptions: jest.fn(),
  })),
  addLineSeries: jest.fn(() => ({
    setData: jest.fn(),
    update: jest.fn(),
    priceScale: jest.fn(() => ({
      applyOptions: jest.fn(),
    })),
    applyOptions: jest.fn(),
  })),
  timeScale: jest.fn(() => ({
    fitContent: jest.fn(),
    scrollToPosition: jest.fn(),
    setVisibleRange: jest.fn(),
    applyOptions: jest.fn(),
  })),
  priceScale: jest.fn(() => ({
    applyOptions: jest.fn(),
  })),
  remove: jest.fn(),
  resize: jest.fn(),
  applyOptions: jest.fn(),
  subscribeCrosshairMove: jest.fn(),
  unsubscribeCrosshairMove: jest.fn(),
}));

module.exports = {
  createChart,
  CrosshairMode: {
    Normal: 0,
    Hidden: 1,
  },
  LineStyle: {
    Solid: 0,
    Dotted: 1,
    Dashed: 2,
    LargeDashed: 3,
    SparseDotted: 4,
  },
  PriceScaleMode: {
    Normal: 0,
    Logarithmic: 1,
    Percentage: 2,
    IndexedTo100: 3,
  },
};
