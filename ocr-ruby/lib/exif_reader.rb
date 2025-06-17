# ExifRライブラリはオプショナル（デモモード用）
begin
  require 'exifr/jpeg'
  EXIFR_AVAILABLE = true
rescue LoadError
  EXIFR_AVAILABLE = false
end

# EXIF情報から撮影日時を取得するクラス
class ExifReader
  # EXIF情報から撮影日時を取得
  # @param image_path [String] 画像ファイルのパス
  # @return [Time, nil] 撮影日時、取得できない場合はnil
  def self.capture_time(image_path)
    return nil unless File.exist?(image_path)
    
    # EXIFRライブラリが利用できない場合はダミー時刻を生成
    unless EXIFR_AVAILABLE
      return generate_demo_capture_time(image_path)
    end
    
    exif = EXIFR::JPEG.new(image_path)
    return nil unless exif&.exif?
    
    # 撮影日時の優先順位: DateTimeOriginal > DateTime > DateTimeDigitized
    exif.date_time_original || exif.date_time || exif.date_time_digitized
  rescue => e
    puts "EXIF読み取りエラー (#{File.basename(image_path)}): #{e.message}"
    nil
  end
  
  # EXIF撮影日時 → ファイル更新日時の順でフォールバック
  # @param image_path [String] 画像ファイルのパス  
  # @return [Time, nil] 撮影日時またはファイル更新日時
  def self.capture_time_with_fallback(image_path)
    # まずEXIF情報を試す
    capture_time = self.capture_time(image_path)
    return capture_time if capture_time
    
    # EXIFが取得できない場合はファイル更新日時
    File.mtime(image_path)
  rescue => e
    puts "時刻取得エラー (#{File.basename(image_path)}): #{e.message}"
    nil
  end
  
  # デバッグ用: EXIF時刻とファイル時刻を比較
  # @param image_path [String] 画像ファイルのパス
  # @return [Hash] 時刻情報の比較結果
  def self.compare_times(image_path)
    exif_time = capture_time(image_path)
    file_time = File.mtime(image_path)
    
    result = {
      image_path: image_path,
      exif_time: exif_time,
      file_time: file_time,
      time_diff_seconds: nil
    }
    
    if exif_time && file_time
      result[:time_diff_seconds] = (exif_time - file_time).abs
    end
    
    result
  rescue => e
    { 
      image_path: image_path, 
      error: e.message,
      exif_time: nil,
      file_time: nil
    }
  end

  # デモモード用のダミー撮影時刻生成
  # ファイル名から数字を抽出して、それに基づいて時刻を生成
  def self.generate_demo_capture_time(image_path)
    filename = File.basename(image_path, '.*')
    number = filename.scan(/\d+/).last.to_i
    
    # 基準時刻: 2024/5/30 10:00:00
    base_time = Time.new(2024, 5, 30, 10, 0, 0)
    
    # ファイル番号に基づいて時刻をずらす（1分間隔）
    demo_time = base_time + (number * 60)
    
    demo_time
  end
end
