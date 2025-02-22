import { View, Text } from '@tarojs/components'
import { useState } from 'react'
import './index.scss'

interface CalendarProps {
  events?: CourseEvent[]
  onCheckIn?: (event: CourseEvent) => void
}

interface CourseEvent {
  date: string
  title: string
  time: string
  checked?: boolean
  class_date?: string
  class_time?: string
  class_name?: string
  class_location?: string
  class_instructor?: string
  class_score_stars?: number
}

const Calendar: React.FC<CalendarProps> = ({ events = [], onCheckIn }) => {
  const [currentMonth, setCurrentMonth] = useState(new Date())

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    return new Date(year, month + 1, 0).getDate()
  }

  const getFirstDayOfMonth = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    return new Date(year, month, 1).getDay()
  }

  const formatDateToChineseFormat = (date: Date) => {
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const weekDay = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
    return `${month}.${day} 周${weekDay}`
  }

  const renderStars = (stars?: number) => {
    if (!stars) return ''
    return '⭐'.repeat(stars)
  }

  const isEventPast = (event: CourseEvent) => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const eventDate = event.class_date || event.date
    
    if (eventDate < today) return true
    if (eventDate === today) {
      const [endTime] = (event.class_time || event.time).split('-').slice(-1)
      const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0')
      return endTime < currentTime
    }
    return false
  }

  const isFutureCourse = (event: CourseEvent) => {
    const now = new Date()
    const today = formatDateToChineseFormat(now)
    const eventDate = event.class_date || event.date
    return eventDate > today
  }

  const getEventClassName = (event: CourseEvent) => {
    if (event.checked) return 'checked'
    if (isEventPast(event)) return 'past'
    if (isFutureCourse(event)) return 'future'
    return ''
  }

  const handleEventClick = (event: CourseEvent) => {
    if (onCheckIn) {
      onCheckIn(event)
    }
  }

  const renderCalendar = () => {
    const daysInMonth = getDaysInMonth(currentMonth)
    const firstDay = getFirstDayOfMonth(currentMonth)
    const days: JSX.Element[] = []

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      days.push(<View key={`empty-${i}`} className='day empty' />)
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const currentDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
      const dateStr = formatDateToChineseFormat(currentDate)
      const dayEvents = events.filter(event => event.class_date === dateStr || event.date === dateStr)

      days.push(
        <View key={day} className={`day ${dayEvents.length ? 'has-event' : ''}`}>
          <View className='day-content'>
            <Text className='day-number'>{day}</Text>
            <View className='events-container'>
              {dayEvents.map((event, index) => (
                <View 
                  key={index} 
                  className={`event-indicator ${getEventClassName(event)}`}
                  onClick={() => handleEventClick(event)}
                >
                  <Text className='event-title'>{event.class_name || event.title}</Text>
                  <Text className='event-time'>{event.class_time || event.time}</Text>
                  <Text className='event-details'>
                    {event.class_location && `📍${event.class_location}`}
                    {event.class_instructor && ` 👤${event.class_instructor}`}
                    {event.class_score_stars && ` ${renderStars(event.class_score_stars)}`}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </View>
      )
    }

    return days
  }

  return (
    <View className='calendar'>
      <View className='calendar-header'>
        <Text 
          className='nav-button' 
          onClick={() => setCurrentMonth(new Date(currentMonth.setMonth(currentMonth.getMonth() - 1)))}
        >
          {'<'}
        </Text>
        <Text className='month-year'>
          {currentMonth.toLocaleString('zh-CN', { year: 'numeric', month: 'long' })}
        </Text>
        <Text 
          className='nav-button'
          onClick={() => setCurrentMonth(new Date(currentMonth.setMonth(currentMonth.getMonth() + 1)))}
        >
          {'>'}
        </Text>
      </View>
      <View className='weekdays'>
        {['日', '一', '二', '三', '四', '五', '六'].map(day => (
          <Text key={day} className='weekday'>{day}</Text>
        ))}
      </View>
      <View className='days-grid'>
        {renderCalendar()}
      </View>
    </View>
  )
}

export default Calendar 