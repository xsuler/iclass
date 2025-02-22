import { View, Text } from '@tarojs/components'
import { AtButton } from 'taro-ui'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import './ImageUploadDialog.scss'

interface ImageUploadDialogProps {
  isOpen: boolean
  onClose: () => void
  onUpload: (courses: any[]) => void
}

const ImageUploadDialog = ({ isOpen, onClose, onUpload }: ImageUploadDialogProps) => {
  const [error, setError] = useState('')
  const [isUploading, setIsUploading] = useState(false)

  if (!isOpen) return null

  const handleChooseImage = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera']
      })

      setIsUploading(true)
      setError('')

      // 上传图片到服务器
      const uploadRes = await Taro.uploadFile({
        url: 'http://localhost:5000/upload',
        filePath: res.tempFilePaths[0],
        name: 'file',
        formData: {
          type: 'course_schedule'
        }
      })

      if (uploadRes.statusCode === 200) {
        const data = JSON.parse(uploadRes.data)
        if (data.courses && data.courses.length > 0) {
          onUpload(data.courses)
          onClose()
        } else {
          setError('未能识别课程信息，请重试')
        }
      } else {
        setError('上传失败，请重试')
      }
    } catch (err) {
      console.error('Upload error:', err)
      setError('选择或上传图片失败，请重试')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <View className='image-upload-dialog'>
      <View className='dialog-content'>
        <View className='dialog-header'>
          <Text className='title'>上传图片</Text>
          <Text className='close' onClick={onClose}>×</Text>
        </View>
        
        {error && (
          <View className='error-message'>
            <Text>{error}</Text>
          </View>
        )}

        <View 
          className='upload-box' 
          onClick={isUploading ? undefined : handleChooseImage}
          style={{ cursor: isUploading ? 'not-allowed' : 'pointer', opacity: isUploading ? 0.7 : 1 }}
        >
          {isUploading ? (
            <View className='upload-placeholder'>
              <Text className='icon'>⏳</Text>
              <Text className='text'>正在上传中...</Text>
              <Text className='hint'>请稍候</Text>
            </View>
          ) : (
            <View className='upload-placeholder'>
              <Text className='icon'>📸</Text>
              <Text className='text'>点击上传图片</Text>
              <Text className='hint'>支持拍照或从相册选择</Text>
            </View>
          )}
        </View>

        <View className='button-group'>
          <AtButton onClick={onClose}>取消</AtButton>
        </View>
      </View>
    </View>
  )
}

export default ImageUploadDialog 