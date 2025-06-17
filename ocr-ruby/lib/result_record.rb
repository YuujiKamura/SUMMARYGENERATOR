require_relative 'survey_point'

# OCR結果を格納するレコードクラス
class ResultRecord
  attr_accessor :filename, :image_path, :capture_time, :bbox
  attr_accessor :location_value, :date_value, :count_value
  attr_accessor :inferred_location, :inferred_date_count
  attr_accessor :ocr_skipped, :ocr_skip_reason
  
  def initialize(
    filename: nil,
    image_path: nil,
    capture_time: nil,
    bbox: nil,
    location_value: nil,
    date_value: nil,
    count_value: nil,
    inferred_location: nil,
    inferred_date_count: nil,
    ocr_skipped: false,
    ocr_skip_reason: nil
  )
    @filename = filename
    @image_path = image_path
    @capture_time = capture_time
    @bbox = bbox
    @location_value = location_value
    @date_value = date_value
    @count_value = count_value
    @inferred_location = inferred_location
    @inferred_date_count = inferred_date_count
    @ocr_skipped = ocr_skipped
    @ocr_skip_reason = ocr_skip_reason
  end
  
  # 生データから ResultRecord を作成
  # @param raw_data [Hash] OCR処理の生データ
  # @return [ResultRecord] 作成されたレコード
  def self.from_raw(raw_data)
    new(
      filename: raw_data['filename'],
      image_path: raw_data['image_path'],
      capture_time: raw_data['capture_time'],
      bbox: raw_data['bbox'],
      location_value: raw_data['location_value'],
      date_value: raw_data['date_value'],
      count_value: raw_data['count_value'],
      ocr_skipped: raw_data['ocr_skipped'],
      ocr_skip_reason: raw_data['ocr_skip_reason']
    )
  end
  
  # 測点情報を持っているか（完全な情報）
  # @return [Boolean] 完全な測点情報があるかどうか
  def located?
    return false unless has_location?
    !SurveyPoint.incomplete_location?(location_value)
  end
  
  # 測点情報を持っているか（値の存在チェックのみ）
  # @return [Boolean] location_value が存在するか
  def has_location?
    !location_value.nil? && !location_value.empty?
  end
  
  # 日付・台数情報を持っているか
  # @return [Boolean] 日付または台数情報があるか
  def has_date_count?
    (!date_value.nil? && !date_value.empty?) || 
    (!count_value.nil? && !count_value.empty?)
  end
  
  # 特定の情報が不足しているか
  # @param key [String] チェックするキー ('location', 'date_count')
  # @return [Boolean] 情報が不足しているか
  def needs?(key)
    case key
    when 'location'
      !located?  # 完全な測点情報が無い場合は補完が必要
    when 'date_count'
      !has_date_count?
    else
      false
    end
  end
  
  # 他のレコードから情報を補完
  # @param other [ResultRecord] 補完元のレコード
  # @param keys [Array<String>] 補完するキーのリスト
  # @return [Boolean] 補完が実行されたかどうか
  def supplement_from(other, keys = ['location', 'date_count'])
    changed = false
    
    keys.each do |key|
      if needs?(key)
        case key
        when 'location'
          if other.located?
            @inferred_location = other.location_value
            changed = true
            puts "  補完実行: #{File.basename(image_path)} <- #{File.basename(other.image_path)} (location: #{other.location_value})"
          end
        when 'date_count'
          if other.has_date_count?
            # 日付・台数をパイプ区切りで結合
            date_count_str = [other.date_value, other.count_value].compact.join('|')
            @inferred_date_count = date_count_str unless date_count_str.empty?
            changed = true
            puts "  補完実行: #{File.basename(image_path)} <- #{File.basename(other.image_path)} (date_count: #{date_count_str})"
          end
        end
      end
    end
    
    changed
  end
  
  # 他のレコードとの撮影時刻差を計算
  # @param other [ResultRecord] 比較対象のレコード
  # @return [Float, nil] 時刻差（秒）、計算できない場合はnil
  def time_diff(other)
    return nil unless capture_time && other.capture_time
    (capture_time - other.capture_time).abs
  end
  
  # 近接する他のレコードから情報を補完
  # @param neighbors [Array<ResultRecord>] 前後のレコード
  # @param time_window [Integer] 補完対象とする時刻差の上限（秒）
  def supplement_from_neighbors(neighbors, time_window = 300)
    return unless neighbors && !neighbors.empty?
    
    # 補完が必要かチェック
    needs_location = needs?('location')
    needs_date_count = needs?('date_count')
    return unless needs_location || needs_date_count
    
    # 撮影時刻の近い順にソート
    sorted_neighbors = neighbors
      .select { |n| n.capture_time && capture_time }
      .sort_by { |n| time_diff(n) }
    
    sorted_neighbors.each do |neighbor|
      diff = time_diff(neighbor)
      next if diff.nil? || diff > time_window
      
      # 補完実行
      keys_to_supplement = []
      keys_to_supplement << 'location' if needs_location
      keys_to_supplement << 'date_count' if needs_date_count
      
      if supplement_from(neighbor, keys_to_supplement)
        puts "    時刻差: #{diff.round(1)}秒"
        break  # 1つ補完できたら終了
      end
    end
  end
  
  # Hash形式で出力
  # @return [Hash] レコードの内容
  def to_hash
    {
      'filename' => filename,
      'image_path' => image_path,
      'capture_time' => capture_time&.to_f,
      'bbox' => bbox,
      'location_value' => location_value,
      'date_value' => date_value,
      'count_value' => count_value,
      'inferred_location' => inferred_location,
      'inferred_date_count' => inferred_date_count,
      'ocr_skipped' => ocr_skipped,
      'ocr_skip_reason' => ocr_skip_reason
    }
  end
  
  # Hash形式で出力（エイリアス）
  alias_method :to_h, :to_hash

  # JSON形式で出力
  def to_json(*args)
    to_hash.to_json(*args)
  end

  # 補完が行われたかどうかを判定
  # @return [Boolean] 補完が行われた場合true
  def supplemented?
    !inferred_location.nil? || !inferred_date_count.nil?
  end

  # Survey Point情報をフォーマット済み文字列で取得
  def formatted_survey_point
    parts = []
    parts << (inferred_location || location_value) if (inferred_location || location_value)
    parts << (inferred_date_count || [date_value, count_value].compact.join(' ')) if (inferred_date_count || date_value || count_value)
    parts.empty? ? nil : parts.join(' ')
  end
end
