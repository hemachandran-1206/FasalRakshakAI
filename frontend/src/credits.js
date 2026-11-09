// Team and credits shown on the About page. Edit this file to change names or sources — no other code needs to change.
// `license` is what the owner publishes; "check" notes mean the licence was unclear when this was written.
export const TEAM_TITLE = "HS202 2026";
// Name, entry number. Add or reorder rows here; the About page renders them as a table.
export const TEAM = [
  { name: "Hemachandran V", entry: "2024CSB1349" },
  { name: "Malothu Jeswanth", entry: "2024CSB1129" },
  { name: "Maloth Anil", entry: "2024CSB1128" },
  { name: "Borelli Sujay Kumar", entry: "2024CSB1110" },
  { name: "Para Arun Gopi Chandu", entry: "2024CSB1138" },
  { name: "Nutalapati Vivek", entry: "2024CSB1136" },
  { name: "Badavath Naveen", entry: "2024CSB1107" },
  { name: "Shaik Hazrath Bilal", entry: "2024CSB1152" },
  { name: "Yenuganti Hemanath", entry: "2024CSB1172" },
  { name: "Rathlavath Jashvanth", entry: "2024CSB1376" },
];

export const CREDITS = [
  { group: "AI models",
    items: [
      { name: "MobileNetV2", by: "Sandler, Howard, Zhu, Zhmoginov, Chen (Google), CVPR 2018", license: "Paper / architecture", url: "https://arxiv.org/abs/1801.04381" },
      { name: "Plant-disease classifier weights (linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification)", by: "linkanjarad on Hugging Face, fine-tuned from google/mobilenet_v2_1.0_224", license: "Declared “other” — confirm terms before wide release", url: "https://huggingface.co/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification" },
      { name: "Pest detector (Yudsky/pest-detection-yolo11)", by: "Yudsky on Hugging Face; trained on the IP102 YOLO-format dataset by leonidkulyk (Kaggle)", license: "MIT", url: "https://huggingface.co/Yudsky/pest-detection-yolo11" },
      { name: "Ultralytics YOLO11", by: "Ultralytics", license: "AGPL-3.0", url: "https://github.com/ultralytics/ultralytics" },
      { name: "Hugging Face Transformers", by: "Hugging Face", license: "Apache-2.0", url: "https://github.com/huggingface/transformers" },
      { name: "PyTorch", by: "PyTorch contributors", license: "BSD-style", url: "https://pytorch.org" },
    ] },
  { group: "Datasets behind the models",
    items: [
      { name: "PlantVillage", by: "Hughes & Salathé, 2015 — “An open access repository of images on plant health”", license: "Open dataset (check the mirror you use)", url: "https://arxiv.org/abs/1511.08060" },
      { name: "PlantDoc", by: "Singh et al., CODS-COMAD 2020 — field images used for evaluation", license: "Open dataset (check the repository)", url: "https://github.com/pratikkayal/PlantDoc-Dataset" },
      { name: "IP102", by: "Wu et al., CVPR 2019 — large-scale insect pest benchmark", license: "Research use", url: "https://github.com/xpwu95/IP102" },
    ] },
  { group: "Agronomy and weather",
    items: [
      { name: "Late-blight risk rule (JHULSACAST)", by: "ICAR-Central Potato Research Institute and Punjab studies, Indian Potato Journal", license: "Published research", url: "https://epubs.icar.org.in/index.php/PotatoJ/article/view/32182" },
      { name: "Late blight forecasting notes", by: "ICAR-CPRI", license: "Published guidance", url: "https://cpri.icar.gov.in/AddLink/getIMG/6065" },
      { name: "Package of practices (rabi)", by: "Punjab Agricultural University (PAU)", license: "Published guidance", url: "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf" },
      { name: "Weather data by Open-Meteo.com", by: "Open-Meteo", license: "CC BY 4.0 (free for non-commercial use)", url: "https://open-meteo.com/" },
    ] },
  { group: "Maps",
    items: [
      { name: "© OpenStreetMap contributors", by: "OpenStreetMap community", license: "ODbL", url: "https://www.openstreetmap.org/copyright" },
      { name: "Leaflet", by: "Volodymyr Agafonkin and contributors", license: "BSD-2-Clause", url: "https://leafletjs.com" },
      { name: "React-Leaflet", by: "Paul Le Cam and contributors", license: "MIT", url: "https://react-leaflet.js.org" },
    ] },
  { group: "Design",
    items: [
      { name: "Manrope", by: "Mikhail Sharanda", license: "SIL Open Font License 1.1", url: "https://fonts.google.com/specimen/Manrope" },
      { name: "Instrument Serif", by: "Rodrigo Fuenzalida and Jordan Egstad (Instrument)", license: "SIL Open Font License 1.1", url: "https://fonts.google.com/specimen/Instrument+Serif" },
      { name: "“Lumo” UI concept", by: "Kris Anfalova — visual inspiration only; no assets were copied", license: "Inspiration", url: "" },
    ] },
  { group: "Software we build on",
    items: [
      { name: "React", by: "Meta and contributors", license: "MIT", url: "https://react.dev" },
      { name: "Vite", by: "Evan You and contributors", license: "MIT", url: "https://vite.dev" },
      { name: "FastAPI", by: "Sebastián Ramírez and contributors", license: "MIT", url: "https://fastapi.tiangolo.com" },
      { name: "SQLAlchemy", by: "Mike Bayer and contributors", license: "MIT", url: "https://www.sqlalchemy.org" },
      { name: "Pydantic", by: "Samuel Colvin and contributors", license: "MIT", url: "https://docs.pydantic.dev" },
      { name: "PostgreSQL", by: "PostgreSQL Global Development Group", license: "PostgreSQL Licence", url: "https://www.postgresql.org" },
      { name: "argon2-cffi, PyJWT, Pillow, NumPy", by: "Their maintainers", license: "MIT / HPND / BSD", url: "https://pypi.org" },
    ] },
];
