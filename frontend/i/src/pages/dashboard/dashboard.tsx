import { View, Text } from '@tarojs/components'
import { useState, useEffect, useMemo } from 'react'
import Calendar from '../../components/Calendar'
import './dashboard.scss'
import Taro from '@tarojs/taro'
import { AtFab } from 'taro-ui'
import ImageUploadDialog from '../../components/ImageUploadDialog'


interface CourseEvent {
  date: string
  title: string
  time: string
  completed?: boolean
  checked?: boolean
  class_date?: string
  class_time?: string
  class_name?: string
  class_location?: string
  class_instructor?: string
  class_score_stars?: number
}

interface Course {
  class_date: string
  class_time: string
  class_name: string
  class_location?: string
  class_instructor?: string
  class_score_stars?: number
  checked?: boolean
}

interface Stats {
  totalCourses: number
  completedCourses: number
  upcomingCourses: number
  averageStars: number
  mostFrequentType: string
  mostFrequentInstructor: string
  courseTypes: { [key: string]: number }
  weekdayStats: { [key: string]: number }
  timeSlotStats: { [key: string]: number }
  instructors: { [key: string]: number }
  dailyCompletion: { date: string; count: number }[]
}

// Helper function to parse date string
const parseDateString = (dateStr: string): string => {
  // Remove all spaces and handle null/undefined
  const cleanDate = (dateStr || '').trim().replace(/\s+/g, '');
  
  // Match patterns like: MM.DD or M.D
  const dateMatch = cleanDate.match(/^(\d{1,2})\.(\d{1,2})/);
  if (!dateMatch) return '';
  
  const month = dateMatch[1].padStart(2, '0');
  const day = dateMatch[2].padStart(2, '0');
  
  return `${month}.${day}`;
}

const Dashboard = () => {
  const [courseEvents, setCourseEvents] = useState<CourseEvent[]>([])
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false)

  const formatDateToChineseFormat = (date: Date) => {
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const weekDay = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
    return `${month}.${day} 周${weekDay}`
  }

  const isEventPast = (event: CourseEvent) => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const eventDate = parseDateString(event.class_date || event.date)
    
    if (eventDate < today.split(' ')[0]) return true
    if (eventDate === today.split(' ')[0]) {
      const [endTime] = (event.class_time || event.time).split('-').slice(-1)
      const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0')
      return endTime < currentTime
    }
    return false
  }

  const canCheckIn = (event: CourseEvent) => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const eventDate = event.class_date || event.date
    
    if (eventDate < today) return false
    if (eventDate > today) return false
    
    const [endTime] = (event.class_time || event.time).split('-').slice(-1)
    const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0')
    return currentTime <= endTime
  }

  const isFutureCourse = (event: CourseEvent) => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const eventDate = event.class_date || event.date
    return eventDate > today
  }

  const handleCheckIn = (event: CourseEvent) => {
    if (event.checked) {
      Taro.showToast({
        title: '已打卡，请勿重复打卡',
        icon: 'none',
        duration: 2000
      })
      return
    }

    if (isFutureCourse(event)) {
      Taro.showToast({
        title: '课程未开始，无法打卡',
        icon: 'none',
        duration: 2000
      })
      return
    }

    if (!canCheckIn(event)) {
      Taro.showToast({
        title: '课程已结束，无法打卡',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 显示确认对话框
    Taro.showModal({
      title: '打卡确认',
      content: `是否确认为课程"${event.class_name || event.title}"打卡？\n时间：${event.class_time || event.time}\n地点：${event.class_location || '未知'}\n教练：${event.class_instructor || '未知'}`,
      confirmText: '确认打卡',
      confirmColor: '#22c55e',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          const updatedEvents = courseEvents.map(e => {
            if ((e.class_date || e.date) === (event.class_date || event.date) &&
                (e.class_time || e.time) === (event.class_time || event.time) &&
                (e.class_name || e.title) === (event.class_name || event.title)) {
              return { ...e, checked: true }
            }
            return e
          })

          setCourseEvents(updatedEvents)
          Taro.setStorageSync('selected_courses', updatedEvents)
          
          Taro.showToast({
            title: '打卡成功',
            icon: 'success',
            duration: 2000
          })
        }
      }
    })
  }

  const getTodayCourses = () => {
    const today = formatDateToChineseFormat(new Date())
    return courseEvents
      .filter(event => (event.class_date || event.date) === today)
      .sort((a, b) => {
        const timeA = a.class_time || a.time
        const timeB = b.class_time || b.time
        return timeA.localeCompare(timeB)
      })
  }

  useEffect(() => {
    const storedCourses = Taro.getStorageSync<Course[]>('selected_courses') || []
    const events = storedCourses.map(course => ({
      ...course,
      date: course.class_date,
      title: course.class_name,
      time: course.class_time
    }))
    setCourseEvents(events)
  }, [isUploadDialogOpen])

  const isDuplicateCourse = (course: Course, existingCourses: Course[]) => {
    const formatKey = (c: Course) => {
      const date = parseDateString(c.class_date || '')
      const time = (c.class_time || '').trim()
      return `${date}-${time}`
    }
    
    const courseKey = formatKey(course)
    return existingCourses.some(existing => formatKey(existing) === courseKey)
  }

  const handleUpload = (courses: Course[]) => {
    // 获取现有课程
    const existingCourses = Taro.getStorageSync<Course[]>('selected_courses') || []
    
    // 过滤掉重复的课程
    const newUniqueCourses = courses.filter(course => !isDuplicateCourse(course, existingCourses))
    
    if (newUniqueCourses.length === 0) {
      // 如果所有课程都是重复的，显示提示
      Taro.showToast({
        title: '课程已存在',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 保存非重复课程
    const newCourses = [...existingCourses, ...newUniqueCourses]
    Taro.setStorageSync('selected_courses', newCourses)

    // 刷新页面数据
    const events = newCourses.map(course => ({
      ...course,
      date: course.class_date,
      title: course.class_name,
      time: course.class_time
    }))
    setCourseEvents(events)

    // 显示成功提示，包含重复课程的信息
    const duplicateCount = courses.length - newUniqueCourses.length
    const message = duplicateCount > 0 
      ? `导入${newUniqueCourses.length}节课程，${duplicateCount}节重复`
      : '课程导入成功'
    
    Taro.showToast({
      title: message,
      icon: 'success',
      duration: 2000
    })
  }

  const todayCourses = getTodayCourses()

  // 计算统计信息
  const stats: Stats = useMemo(() => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0')

    // 统计课程类型和教练
    const courseTypes: { [key: string]: number } = {}
    const instructors: { [key: string]: number } = {}
    const weekdayStats: { [key: string]: number } = {}
    const timeSlotStats: { [key: string]: number } = {}
    let totalStars = 0
    let starsCount = 0

    // 使用Set来存储唯一课程标识
    const uniqueCourses = new Set(courseEvents.map(event => {
      const date = parseDateString(event.class_date || event.date || '')
      const time = (event.class_time || event.time || '').trim()
      return `${date}-${time}`
    }))

    // 获取已打卡的课程
    const checkedCourses = courseEvents.filter(event => !event.checked)

    // 统计每个已打卡课程的详细信息
    checkedCourses.forEach(event => {
      // 统计课程类型
      const courseName = event.class_name || event.title
      const baseType = courseName.split('-')[0]
      courseTypes[baseType] = (courseTypes[baseType] || 0) + 1

      // 统计教练
      if (event.class_instructor) {
        instructors[event.class_instructor] = (instructors[event.class_instructor] || 0) + 1
      }

      // 统计星级
      if (event.class_score_stars) {
        totalStars += event.class_score_stars
        starsCount++
      }

      // 统计星期分布
      const date = new Date(event.class_date?.replace(/\./g, '/') || event.date.replace(/\./g, '/'))
      const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
      weekdayStats[weekday] = (weekdayStats[weekday] || 0) + 1

      // 统计时间段分布
      const time = event.class_time || event.time
      const hour = parseInt(time.split(':')[0])
      let timeSlot = '其他'
      if (hour >= 6 && hour < 9) timeSlot = '早课(6-9点)'
      else if (hour >= 9 && hour < 12) timeSlot = '上午(9-12点)'
      else if (hour >= 12 && hour < 14) timeSlot = '中午(12-14点)'
      else if (hour >= 14 && hour < 18) timeSlot = '下午(14-18点)'
      else if (hour >= 18 && hour < 22) timeSlot = '晚上(18-22点)'
      timeSlotStats[timeSlot] = (timeSlotStats[timeSlot] || 0) + 1
    })

    const completed = checkedCourses.length

    const upcoming = courseEvents.filter(event => {
      const eventDate = event.class_date || event.date
      if (eventDate > today.split(' ')[0]) return true
      if (eventDate === today.split(' ')[0]) {
        const [endTime] = (event.class_time || event.time).split('-').slice(-1)
        return endTime > currentTime
      }
      return false
    }).length

    // 找出最频繁的课程类型和教练
    const mostFrequentType = Object.entries(courseTypes).sort((a, b) => b[1] - a[1])[0]?.[0] || '暂无数据'
    const mostFrequentInstructor = Object.entries(instructors).sort((a, b) => b[1] - a[1])[0]?.[0] || '暂无数据'

    // 新增每日完成统计（过去7天）
    const dailyCompletion: { date: string; count: number }[] = []
    
    // 生成过去7天日期
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now)
      date.setDate(date.getDate() - i)
      const dateStr = formatDateToChineseFormat(date)
      
      const count = courseEvents.filter(event => 
        event.checked && 
        (event.class_date || event.date) === dateStr
      ).length
      
      dailyCompletion.push({
        date: dateStr.split(' ')[0], // 只保留日期部分
        count
      })
    }

    // 修改卡片标题以反映这是已打卡课程的统计
    return {
      totalCourses: uniqueCourses.size,
      completedCourses: completed,
      upcomingCourses: upcoming,
      averageStars: starsCount ? +(totalStars / starsCount).toFixed(1) : 0,
      mostFrequentType,
      mostFrequentInstructor,
      courseTypes,
      weekdayStats,
      timeSlotStats,
      instructors,
      dailyCompletion
    }
  }, [courseEvents])

  return (
    <View className='dashboard-page'>
      <View className='content'>
        {/* 统计卡片 */}
        <View className='stats-grid'>
          <View className='stat-card'>
            <Text className='stat-title'>总课程数</Text>
            <Text className='stat-value'>{stats.totalCourses}</Text>
          </View>
          <View className='stat-card'>
            <Text className='stat-title'>已打卡</Text>
            <Text className='stat-value'>{stats.completedCourses}</Text>
          </View>
          <View className='stat-card'>
            <Text className='stat-title'>待上课</Text>
            <Text className='stat-value'>{stats.upcomingCourses}</Text>
          </View>
        </View>

        {/* 详细报告 */}
        <View className='report-section'>
          <Text className='section-title'>打卡课程报告</Text>
          <View className='report-grid'>
            <View className='report-item'>
              <Text className='report-label'>平均评分</Text>
              <Text className='report-value'>{stats.averageStars} {'⭐'.repeat(Math.round(stats.averageStars))}</Text>
            </View>
            <View className='report-item'>
              <Text className='report-label'>最常打卡</Text>
              <Text className='report-value'>{stats.mostFrequentType}</Text>
            </View>
            <View className='report-item'>
              <Text className='report-label'>常见教练</Text>
              <Text className='report-value'>{stats.mostFrequentInstructor}</Text>
            </View>
          </View>
        </View>

        {/* 统计图表 */}
        <View className='charts-section'>
          <Text className='section-title'>打卡数据分析</Text>
          
          {/* 新增时间趋势图表 */}
          <View className='chart-container'>
            <Text className='chart-title'>每日打卡趋势（近7天）</Text>
            <View className='line-chart'>
              {/* Y轴 */}
              <View className='y-axis'>
                {[0, 2, 4, 6].map(num => (
                  <Text key={num} className='axis-label'>{num}</Text>
                ))}
              </View>
              
              {/* 图表主体 */}
              <View className='chart-content'>
                {stats.dailyCompletion.map((day, index) => (
                  <View 
                    key={day.date}
                    className='data-point'
                    style={{
                      left: `${(index * 100) / 6}%`,
                      bottom: `${(day.count / 6) * 50}%`
                    }}
                  >
                    <View className='point-value'>{day.count}</View>
                    <View className='point-circle' />
                    {index > 0 && (
                      <View 
                        className='line-segment'
                        style={{
                          left: '-50%',
                          height: `${Math.abs(
                            (day.count - stats.dailyCompletion[index - 1].count) * 10
                          )}px`,
                          transform: `rotate(${
                            Math.atan2(
                              day.count - stats.dailyCompletion[index - 1].count,
                              100
                            ) * (180 / Math.PI)
                          }deg)`
                        }}
                      />
                    )}
                  </View>
                ))}
              </View>
              
              {/* X轴 */}
              <View className='x-axis'>
                {stats.dailyCompletion.map(day => (
                  <Text key={day.date} className='axis-label'>{day.date}</Text>
                ))}
              </View>
            </View>
          </View>

          {/* 课程类型分布 */}
          <View className='chart-container'>
            <Text className='chart-title'>课程类型分布</Text>
            <View className='chart-data-grid'>
              {Object.entries(stats.courseTypes).map(([type, count], index) => (
                <View key={type} className='chart-bar-item'>
                  <View 
                    className='chart-bar' 
                    style={{ 
                      height: `${count * 20}px`,
                      backgroundColor: `hsl(${index * 30}, 70%, 60%)`
                    }}
                  >
                    <Text className='chart-value'>{count}</Text>
                  </View>
                  <Text className='chart-label'>{type}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 星期分布 */}
          <View className='chart-container'>
            <Text className='chart-title'>每周课程分布</Text>
            <View className='chart-data-grid'>
              {['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map((day, index) => (
                <View key={day} className='chart-bar-item'>
                  <View 
                    className='chart-bar' 
                    style={{ 
                      height: `${(stats.weekdayStats[day] || 0) * 20}px`,
                      backgroundColor: `hsl(200, 70%, ${50 + index * 5}%)`
                    }}
                  >
                    <Text className='chart-value'>{stats.weekdayStats[day] || 0}</Text>
                  </View>
                  <Text className='chart-label'>{day}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 时间段分布 */}
          <View className='chart-container'>
            <Text className='chart-title'>时间段分布</Text>
            <View className='chart-data-grid'>
              {Object.entries(stats.timeSlotStats).map(([slot, count], index) => (
                <View key={slot} className='chart-bar-item'>
                  <View 
                    className='chart-bar' 
                    style={{ 
                      height: `${count * 20}px`,
                      backgroundColor: `hsl(${120 + index * 30}, 70%, 60%)`
                    }}
                  >
                    <Text className='chart-value'>{count}</Text>
                  </View>
                  <Text className='chart-label'>{slot}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 教练分布 */}
          <View className='chart-container'>
            <Text className='chart-title'>教练课程数量 TOP5</Text>
            <View className='chart-data-grid'>
              {Object.entries(stats.instructors)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([instructor, count], index) => (
                  <View key={instructor} className='chart-bar-item'>
                    <View 
                      className='chart-bar' 
                      style={{ 
                        height: `${count * 20}px`,
                        backgroundColor: `hsl(${280 + index * 20}, 70%, 60%)`
                      }}
                    >
                      <Text className='chart-value'>{count}</Text>
                    </View>
                    <Text className='chart-label'>{instructor}</Text>
                  </View>
                ))}
            </View>
          </View>
        </View>

        <View className='calendar-section'>
          <Text className='section-title'>课程日历</Text>
          <Calendar events={courseEvents} onCheckIn={handleCheckIn} />
        </View>

        <View className='today-courses'>
          <Text className='section-title'>今日课程</Text>
          {todayCourses.length > 0 ? (
            todayCourses.map((course, index) => (
              <View 
                key={index} 
                className={`course-item ${isEventPast(course) ? 'past' : ''} ${course.checked ? 'checked' : ''}`}
                onClick={() => handleCheckIn(course)}
              >
                <Text className='time'>{course.class_time || course.time}</Text>
                <View className='details'>
                  <Text className='title'>{course.class_name || course.title}</Text>
                  {course.class_location && (
                    <Text className='location'>📍 {course.class_location}</Text>
                  )}
                </View>
                {course.class_instructor && (
                  <Text className='instructor'>👤 {course.class_instructor}</Text>
                )}
              </View>
            ))
          ) : (
            <View className='no-courses'>
              <Text>今天没有课程安排</Text>
            </View>
          )}
        </View>
      </View>

      {/* 底部上传按钮 */}
      <View className='fab-container'>
        <AtFab onClick={() => setIsUploadDialogOpen(true)}>
          <Text className='fab-icon'>📸</Text>
        </AtFab>
      </View>

      {/* 上传对话框 */}
      <ImageUploadDialog
        isOpen={isUploadDialogOpen}
        onClose={() => setIsUploadDialogOpen(false)}
        onUpload={handleUpload}
      />
    </View>
  )
}

export default Dashboard 