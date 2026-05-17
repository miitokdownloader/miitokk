/* ── STATE ────────────────────────────────────── */
let selectedQuality = 'best';
let isDownloading   = false;
let previewData     = null;
let previewTimer    = null;
let photoUrls       = [];
let isPhotoMode     = false;
let lastPreviewUrl  = null;

const qualityLabel = { best:'BEST', '1080':'1080P', '720':'720P', photo:'PHOTO' };
const typeLabel    = { best:'MP4', '1080':'MP4', '720':'MP4', photo:'IMAGE' };
