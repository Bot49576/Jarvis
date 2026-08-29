export const dashboardConfig = {
  theme: {
    accent: '#20d9ed',
    panelRadius: '12px',
    panelGap: '12px',
    leftRail: 'minmax(210px, 270px)',
    rightRail: 'minmax(330px, 440px)',
  },
  leftModules: [
    {
      id: 'foundation',
      enabled: true,
      title: 'SYSTEM // BASIS',
      badge: 'STUFE 01',
      type: 'metrics',
      items: [
        ['PWA', 'AKTIV'],
        ['Dashboard-API', 'STUFE 02'],
        ['Gerätefreigabe', 'STUFE 03'],
      ],
    },
    {
      id: 'separation',
      enabled: true,
      desktopOnly: true,
      title: 'SICHERHEIT',
      badge: 'GETRENNT',
      type: 'note',
      text: 'Die Schnittstelle ist vorbereitet. Ohne die einmalige Gerätefreigabe aus Stufe 03 bleiben Chat, Sessions und Status sicher gesperrt.',
    },
  ],
  quickActions: [
    { id: 'search-demo', enabled: true, label: 'ANTWORTSUCHE', hint: 'Gelb testen', available: true },
    { id: 'voice-demo', enabled: true, label: 'STIMME', hint: 'Ausschlag testen', available: true },
    { id: 'error-demo', enabled: true, label: 'FEHLER', hint: 'Rot testen', available: true },
    { id: 'offline-demo', enabled: true, label: 'OFFLINE', hint: 'Rot testen', available: true },
    { id: 'reset', enabled: true, label: 'RESET', hint: 'Standardzustand', available: true },
    { id: 'research', enabled: true, label: 'RECHERCHE', hint: 'ab Stufe 02', available: false },
  ],
};
