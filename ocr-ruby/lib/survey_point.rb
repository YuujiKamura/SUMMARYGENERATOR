# Survey Point（測点）補完のためのユーティリティクラス
class SurveyPoint
  # 許容する撮影時刻差（秒）- 5分
  DEFAULT_TIME_WINDOW = 300
  
  # 近傍エントリの値も考慮して不完全か判定
  # neighbors: Array<String> 直前・直後など近接エントリの location 値を渡す
  def self.incomplete_location?(location, neighbors = [])
    return true if location.nil? || location.strip.empty?

    loc = location.strip

    # --- 基本的な短絡判定 ----------------------------------
    return true if loc.length < 2 # 2文字未満は不完全

    # 数字のみ / 記号のみ
    return true if loc =~ /^\d+$/
    return true if loc =~ /^[^\p{Alnum}]+$/

    # 代表的な不完全ワード
    incomplete_words = %w[
      No. No no. no N/A n/a NA na
      小山 大山 東区 西区 南区 北区 中央 本町 新町
      山 川 橋 駅 町 市 区 村
    ]
    return true if incomplete_words.include?(loc)

    # "区:" で始まるパターン
    return true if loc.start_with?('区:')

    # 'No.' が含まれる場合の詳細判定
    if loc =~ /No\./i
      # 完全形: "No. 25 小山" 等 → 地名と数字が両方含まれる
      # 不完全: 数字の無い No. / 地名の無い No.XX
      after_no = loc.split(/No\./i, 2)[1]&.strip || ''
      # 数字を含まない or 地名を含まない場合は不完全
      if after_no.empty? || !(after_no =~ /\d/)
        return true
      end
    end

    # loc に "No." が含まれない単独地名のみの場合 → 近傍に同一が無ければ不完全
    unless loc =~ /No\./i
      neighbor_vals = neighbors.compact.map(&:strip)
      return true unless neighbor_vals.any? { |v| v == loc }
    end

    false
  end
  
  # 完全な測点情報を持つレコードから時刻-場所のルックアップテーブルを構築
  # @param records [Array<ResultRecord>] 全レコード
  # @return [Array<Array>] [[time, location], ...] の配列
  def self.build_time_lookup(records)
    lookup = []
    
    records.each do |record|
      next unless record.capture_time && record.location_value
      
      # 完全な場所情報のみを補完元として使用
      unless incomplete_location?(record.location_value)
        lookup << [record.capture_time, record.location_value]
      end
    end
    
    # 時刻順でソート
    lookup.sort_by { |time, _| time }
  end
  
  # 撮影時刻が近いレコードから場所を推定
  # @param target_time [Time] 対象の撮影時刻
  # @param time_lookup [Array] build_time_lookupで構築したルックアップテーブル
  # @param time_window [Integer] 許容する時刻差（秒）
  # @return [String, nil] 推定された場所、見つからない場合はnil
  def self.infer_location(target_time, time_lookup, time_window = DEFAULT_TIME_WINDOW)
    return nil unless target_time && !time_lookup.empty?
    
    # 最も近い時刻のレコードを見つける
    closest = time_lookup.min_by do |time, _|
      (target_time - time).abs
    end
    
    return nil unless closest
    
    closest_time, closest_location = closest
    time_diff = (target_time - closest_time).abs
    
    # 時刻差が許容範囲内であれば推定結果として返す
    time_diff <= time_window ? closest_location : nil
  end
  
  # 全レコードに対して場所情報の推定・補完を実行
  # @param records [Array<ResultRecord>] 全レコード
  # @param time_window [Integer] 許容する時刻差（秒）
  # @return [Array<ResultRecord>] 補完処理済みのレコード
  def self.supplement_all_locations(records, time_window = DEFAULT_TIME_WINDOW)
    return records if records.empty?
    
    # 完全な測点情報からルックアップテーブルを構築
    time_lookup = build_time_lookup(records)
    puts "補完元となる完全な測点情報: #{time_lookup.size}件"
    
    supplemented_count = 0
    
    records.each do |record|
      # 不完全な場所情報を持つレコードに対して推定を実行
      if record.needs?('location') && record.capture_time
        inferred = infer_location(record.capture_time, time_lookup, time_window)
        if inferred
          record.inferred_location = inferred
          supplemented_count += 1
          puts "場所推定: #{File.basename(record.image_path)} -> #{inferred}"
        end
      end
    end
    
    puts "場所情報補完数: #{supplemented_count}件"
    records
  end
  
  # 統計情報を出力
  # @param records [Array<ResultRecord>] 全レコード
  def self.print_statistics(records)
    total = records.size
    located_count = records.count(&:located?)
    inferred_count = records.count { |r| r.inferred_location }
    missing_count = total - located_count - inferred_count
    date_count_count = records.count(&:has_date_count?)

    puts "\n=== Survey Point 統計情報 ==="
    puts "総処理ファイル数: #{total}"
    puts "測点名称検出数 (OCR成功): #{located_count}"
    puts "測点名称補完数: #{inferred_count}"
    puts "未取得: #{missing_count}"
    puts "日付・台数検出数: #{date_count_count}"
  end

  # -------- インスタンス属性 --------
  attr_accessor :filename, :image_path, :capture_time, :bbox
  attr_accessor :location_value, :date_value, :count_value
  attr_accessor :inferred_location, :inferred_date_count
  attr_accessor :ocr_skipped, :ocr_skip_reason, :from_cache

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
    ocr_skip_reason: nil,
    from_cache: false
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
    @from_cache = from_cache
  end

  # ---------- factory ----------
  def self.from_raw(raw)
    new(
      filename: raw['filename'],
      image_path: raw['image_path'],
      capture_time: raw['capture_time'] ? Time.at(raw['capture_time'].to_f) : nil,
      bbox: raw['bbox'],
      location_value: raw['location_value'],
      date_value: raw['date_value'],
      count_value: raw['count_value'],
      ocr_skipped: raw['ocr_skipped'],
      ocr_skip_reason: raw['ocr_skip_reason'],
      from_cache: raw['from_cache']
    )
  end

  # ---------- 状態判定 ----------
  def has_location?
    !location_value.nil? && !location_value.empty?
  end

  def located?
    has_location? && !SurveyPoint.incomplete_location?(location_value)
  end

  def has_date_count?
    (!date_value.nil? && !date_value.empty?) || (!count_value.nil? && !count_value.empty?)
  end

  def needs?(key)
    case key
    when 'location'
      !located?
    when 'date_count'
      !has_date_count?
    else
      false
    end
  end

  # ---------- 補完処理 ----------
  def supplement_from(other, keys = ['location', 'date_count'])
    changed = false
    keys.each do |key|
      next unless needs?(key)
      case key
      when 'location'
        if other.located?
          @inferred_location = other.location_value
          changed = true
        end
      when 'date_count'
        if other.has_date_count?
          @inferred_date_count = [other.date_value, other.count_value].compact.join('|')
          changed = true
        end
      end
    end
    changed
  end

  def time_diff(other)
    return nil unless capture_time && other.capture_time
    (capture_time - other.capture_time).abs
  end

  def supplement_from_neighbors(neighbors, time_window = DEFAULT_TIME_WINDOW)
    return if neighbors.empty?
    needed_keys = []
    needed_keys << 'location' if needs?('location')
    needed_keys << 'date_count' if needs?('date_count')
    return if needed_keys.empty?

    neighbors
      .select { |n| n.capture_time && capture_time }
      .sort_by { |n| time_diff(n) }
      .each do |neighbor|
        diff = time_diff(neighbor)
        next if diff.nil? || diff > time_window
        if supplement_from(neighbor, needed_keys)
          break
        end
      end
  end

  # ---------- 出力 ----------
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
      'ocr_skip_reason' => ocr_skip_reason,
      'from_cache' => from_cache
    }
  end
  alias_method :to_h, :to_hash

  def supplemented?
    !inferred_location.nil? || !inferred_date_count.nil?
  end

  def formatted_survey_point
    parts = []
    parts << (inferred_location || location_value) if (inferred_location || location_value)
    parts << (inferred_date_count || [date_value, count_value].compact.join(' ')) if (inferred_date_count || date_value || count_value)
    parts.empty? ? nil : parts.join(' ')
  end

  def photo_category
    if located? || inferred_location
      '測点'
    elsif date_value && count_value
      '日付台数'
    else
      'その他'
    end
  end

  def photo_value
    case photo_category
    when '測点'
      inferred_location || location_value
    when '日付台数'
      [date_value, count_value].compact.join(' ')
    else
      nil
    end
  end

  # 全レコードに対して前後近接エントリからの補完を実行
  #   Python 版 SurveyPoint.supplemented_by_closest と同等の処理
  # @param records [Array<ResultRecord>]
  # @param time_window [Integer] 許容秒差
  # @param keys [Array<String>] 補完対象キー
  def self.supplement_from_neighbors_all(records, time_window = DEFAULT_TIME_WINDOW, keys = ['location', 'date_count'])
    return records if records.empty?

    # capture_time が存在するレコードのみを対象に時刻順で並べ替え
    sorted = records.select { |r| r.capture_time }.sort_by(&:capture_time)
    supplemented = 0

    sorted.each_with_index do |rec, idx|
      needed = keys.select { |k| rec.needs?(k) }
      next if needed.empty?

      prev_rec = idx.positive? ? sorted[idx - 1] : nil
      next_rec = (idx + 1 < sorted.size) ? sorted[idx + 1] : nil

      # 候補レコードの中で時間差が小さいものを選択
      candidates = []
      [prev_rec, next_rec].compact.each do |cand|
        diff = rec.time_diff(cand)
        candidates << [diff, cand] if diff && diff <= time_window
      end
      next if candidates.empty?

      best = candidates.min_by(&:first)[1]
      supplemented += 1 if rec.supplement_from(best, needed)
    end

    puts "前後エントリ補完数: #{supplemented}件" if supplemented > 0
    records
  end
end
