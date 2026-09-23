export interface Metric { label:string; value:string; tone?: 'positive' }
export interface MarketData { asset:string; status:string; metrics:Metric[]; points:number[] }
export async function getMarketData():Promise<MarketData>{
  // Replace this demo adapter with GET /api/market-data when the backend is available.
  return { asset:'AAPL', status:'DEMO DATA · NOT LIVE', metrics:[{label:'Price',value:'$182.63'},{label:'Daily Change',value:'+0.84%',tone:'positive'},{label:'Volume',value:'42.1M'},{label:'Market Status',value:'Closed'}], points:[116,112,126,120,137,129,147,141,159,152,169,163] }
}
