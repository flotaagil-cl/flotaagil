const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto(require('url').pathToFileURL(require('path').join(__dirname, 'guia.html')).href, { waitUntil: 'networkidle' });
  await p.pdf({ path: __dirname + '/Guia_del_proyecto_FlotaAgil.pdf', format: 'A4', printBackground: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>',
    footerTemplate: '<div style="width:100%;font-size:8px;color:#4F6A6C;padding:0 15mm;display:flex;justify-content:space-between;font-family:sans-serif"><span>Gu&iacute;a del proyecto Flota&Aacute;gil</span><span class="pageNumber"></span></div>',
    margin: { top: '14mm', bottom: '16mm', left: '15mm', right: '15mm' } });
  await b.close();
})();
