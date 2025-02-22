export default defineAppConfig({
  pages: [
    'pages/dashboard/dashboard',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#3B82F6',
    navigationBarTitleText: '健康课程管理',
    navigationBarTextStyle: 'white'
  },
  tabBar: {
    color: '#64748b',
    selectedColor: '#3B82F6',
    borderStyle: 'white',
    backgroundColor: '#ffffff',
    list: [
      {
        pagePath: 'pages/dashboard/dashboard',
        text: '📊 数据看板'
      }
    ]
  }
})
