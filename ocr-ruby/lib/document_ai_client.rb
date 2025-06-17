require 'json'

# DocumentAI はオプショナル（デモモード用）
begin
  require 'google/cloud/document_ai'
  DOCUMENTAI_AVAILABLE = true
rescue LoadError
  DOCUMENTAI_AVAILABLE = false
end

# Google Cloud DocumentAI を使用したOCR処理クライアント
class DocumentAIClient
  attr_reader :client, :processor_name, :demo_mode
    def initialize(config_path = nil)
    @config = load_config(config_path)
    @demo_mode = should_use_demo_mode?
    
    if @demo_mode
      puts "デモモードで実行します（ダミーOCRデータを使用）"
      @client = nil
      @processor_name = nil
    else
      setup_production_client
    end
  end
  # 画像からテキストを抽出
  # @param image_path [String] 画像ファイルのパス
  # @return [Hash] OCR結果のハッシュ
  def extract_text(image_path)
    unless File.exist?(image_path)
      return create_error_result(image_path, "ファイルが存在しません")
    end
    
    # デモモードの場合はダミーデータを返す
    if @demo_mode
      return generate_demo_result(image_path)
    end
    
    begin
      # ファイル読み込み
      image_content = File.binread(image_path)
      mime_type = detect_mime_type(image_path)
      
      puts "OCR処理中: #{File.basename(image_path)}"
      
      # DocumentAI リクエスト作成
      request = {
        name: @processor_name,
        raw_document: {
          content: image_content,
          mime_type: mime_type
        }
      }
      
      # DocumentAI API 呼び出し
      response = @client.process_document(request)
      document = response.document
      
      # 結果を解析
      parse_document_result(image_path, document)
      
    rescue => e
      puts "OCRエラー (#{File.basename(image_path)}): #{e.message}"
      create_error_result(image_path, e.message)
    end
  end
  
  private
    # 設定ファイルを読み込み
  def load_config(config_path)
    config_path ||= File.join(__dir__, '../config/document_ai.json')
    
    if File.exist?(config_path)
      config = JSON.parse(File.read(config_path))
      puts "設定ファイルを読み込みました: #{config_path}"
      config
    else
      puts "設定ファイルが見つかりません: #{config_path}"
      puts "環境変数から設定を取得を試行..."
      
      # 環境変数から設定を取得
      env_config = {
        'project_id' => ENV['GOOGLE_CLOUD_PROJECT_ID'],
        'location' => ENV['DOCUMENT_AI_LOCATION'] || 'us',
        'processor_id' => ENV['DOCUMENT_AI_PROCESSOR_ID'],
        'credentials_path' => ENV['GOOGLE_APPLICATION_CREDENTIALS']
      }
      
      if env_config['project_id'] && env_config['processor_id']
        puts "環境変数から設定を取得しました"
        env_config
      else
        puts "環境変数にも必要な設定が見つかりません"
        nil
      end
    end
  rescue JSON::ParserError => e
    puts "設定ファイルのJSON解析エラー: #{e.message}"
    nil
  end
    # プロセッサー名を構築
  def build_processor_name
    project_id = @config['project_id']
    location = @config['location']
    processor_id = @config['processor_id']
    
    unless project_id && location && processor_id
      raise "DocumentAI設定が不完全です。config/document_ai.json を確認してください。"
    end
    
    # Ruby版DocumentAI gemでの正しいプロセッサー名形式
    "projects/#{project_id}/locations/#{location}/processors/#{processor_id}"
  end
  
  # ファイル拡張子からMIMEタイプを推定
  def detect_mime_type(file_path)
    ext = File.extname(file_path).downcase
    case ext
    when '.jpg', '.jpeg'
      'image/jpeg'
    when '.png'
      'image/png'
    when '.pdf'
      'application/pdf'
    else
      'image/jpeg'  # デフォルト
    end
  end
    # DocumentAI の結果を解析してハッシュに変換
  def parse_document_result(image_path, document)
    # 基本テキスト抽出
    ocr_text = document.text || ""
    
    result = {
      'image_path' => image_path,
      'ocr_text' => ocr_text,
      'location_value' => nil,
      'date_value' => nil,
      'count_value' => nil,
      'confidence' => 0.9,  # DocumentAI は一般的に高い精度
      'error' => nil,
      'capture_time' => nil  # ExifReaderで後で設定される
    }
    
    puts "OCR抽出テキスト: #{ocr_text.length > 50 ? ocr_text[0..50] + '...' : ocr_text}"
    
    # パターンマッチングによる値抽出
    extract_by_patterns(result)
    
    result
  end
  
  # バウンディングボックス情報を抽出
  def extract_bounding_box(entity)
    return nil unless entity.page_anchor&.page_refs&.first&.bounding_box
    
    bbox = entity.page_anchor.page_refs.first.bounding_box
    vertices = bbox.vertices
    
    return nil unless vertices && vertices.size >= 4
    
    x_coords = vertices.map(&:x).compact
    y_coords = vertices.map(&:y).compact
    
    return nil if x_coords.empty? || y_coords.empty?
    
    {
      'x1' => x_coords.min,
      'y1' => y_coords.min,
      'x2' => x_coords.max,
      'y2' => y_coords.max,
      'width' => x_coords.max - x_coords.min,
      'height' => y_coords.max - y_coords.min
    }
  end
    # パターンマッチングによるテキスト抽出
  def extract_by_patterns(result)
    text = result['ocr_text'] || ""
    
    puts "パターンマッチング対象テキスト: #{text[0..100]}#{'...' if text.length > 100}"
    
    # 測点パターン: "No. 26", "小山 No.25" など
    location_patterns = [
      /工区[:\s]*([^\s\n]+)/,
      /No\.\s*(\d+)/,
      /(小山|大田原|那須塩原|宇都宮|足利|佐野|栃木|真岡|矢板|塩谷|鹿沼|日光|さくら|大田原|那須烏山|下野)/
    ]
    
    location_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['location_value']
        result['location_value'] = match[1] || match[0]
        puts "場所抽出: #{result['location_value']}"
        break
      end
    end
    
    # 日付パターン: "5/30", "2024/05/30" など
    date_patterns = [
      /(\d{1,2}\/\d{1,2})/,
      /(\d{4}\/\d{1,2}\/\d{1,2})/,
      /(\d{1,2}-\d{1,2})/
    ]
    
    date_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['date_value']
        result['date_value'] = match[1] || match[0]
        puts "日付抽出: #{result['date_value']}"
        break
      end
    end
    
    # 台数パターン: "1台目", "5台" など
    count_patterns = [
      /(\d+台目?)/,
      /(\d+\s*台)/
    ]
    
    count_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['count_value']
        result['count_value'] = match[1] || match[0]
        puts "台数抽出: #{result['count_value']}"
        break
      end
    end
  end
  
  # エラー結果を作成
  def create_error_result(image_path, error_message)
    {
      'filename' => File.basename(image_path),
      'image_path' => image_path,
      'capture_time' => Time.now,
      'bbox' => nil,
      'location_value' => nil,
      'date_value' => nil,
      'count_value' => nil,
      'ocr_skipped' => true,
      'ocr_skip_reason' => error_message,
      'raw_text' => '',
      'entities' => []
    }
  end

  # デモモード用のダミーOCRデータ生成
  def generate_demo_result(image_path)
    filename = File.basename(image_path, '.*')
    
    # ファイル名から番号を抽出してパターンを決定
    number = filename.scan(/\d+/).last.to_i
    
    # ダミーデータのパターン
    demo_patterns = [
      {
        text: "No.1 小山 5/30 1台目",
        location_value: "小山",
        date_value: "5/30",
        count_value: "1台目"
      },
      {
        text: "No.2 大田原 5/30 2台目",
        location_value: "大田原",
        date_value: "5/30",
        count_value: "2台目"
      },
      {
        text: "No.3 那須塩原 6/1 1台目",
        location_value: "那須塩原",
        date_value: "6/1",
        count_value: "1台目"
      },
      {
        text: "No.4 宇都宮 6/1 3台目",
        location_value: "宇都宮",
        date_value: "6/1",
        count_value: "3台目"
      },
      {
        text: "No.",  # 不完全データ（補完対象）
        location_value: nil,
        date_value: nil,
        count_value: nil
      },
      {
        text: "小山",  # 場所のみ（補完対象）
        location_value: "小山",
        date_value: nil,
        count_value: nil
      }
    ]
    
    # ファイル番号に応じてパターンを選択
    pattern_index = (number % demo_patterns.size)
    pattern = demo_patterns[pattern_index]
    
    puts "デモOCR結果: #{File.basename(image_path)} -> '#{pattern[:text]}'"
    
    {
      'image_path' => image_path,
      'ocr_text' => pattern[:text],
      'location_value' => pattern[:location_value],
      'date_value' => pattern[:date_value],
      'count_value' => pattern[:count_value],
      'confidence' => 0.85,
      'error' => nil,
      'capture_time' => nil  # ExifReaderで後で設定される
    }
  end

  # デモモードを使用するかどうかを判定
  def should_use_demo_mode?
    # DocumentAIライブラリが利用できない場合
    return true unless DOCUMENTAI_AVAILABLE
    
    # 設定が不完全な場合
    return true if @config.nil? || @config.empty?
    
    required_keys = ['project_id', 'location', 'processor_id']
    missing_keys = required_keys.select { |key| @config[key].nil? || @config[key].empty? }
    
    return true unless missing_keys.empty?
    
    # プレースホルダー値の場合（実際の設定ではない）
    placeholder_values = ['your-gcp-project-id', 'your-processor-id']
    return true if placeholder_values.include?(@config['project_id']) || 
                   placeholder_values.include?(@config['processor_id'])
    
    false
  end
    # 本番クライアントをセットアップ
  def setup_production_client
    puts "DocumentAI本番モードを初期化中..."
    puts "プロジェクト: #{@config['project_id']}"
    puts "リージョン: #{@config['location']}"
    puts "プロセッサー: #{@config['processor_id']}"
    
    begin
      # 認証情報の設定
      setup_credentials
      
      # DocumentAIクライアント作成
      @client = Google::Cloud::DocumentAI.document_processor_service do |config|
        if @credentials_path && File.exist?(@credentials_path)
          config.credentials = @credentials_path
        end
      end
      
      @processor_name = build_processor_name
      
      puts "DocumentAI接続テスト中..."
      test_connection
      
      puts "DocumentAI初期化完了"
    rescue => e
      puts "DocumentAI初期化エラー: #{e.message}"
      puts "デモモードにフォールバック"
      @demo_mode = true
      @client = nil
      @processor_name = nil
    end
  end
    # 認証情報をセットアップ
  def setup_credentials
    @credentials_path = @config['credentials_path']
    
    if @credentials_path && File.exist?(@credentials_path)
      puts "サービスアカウントキーを使用: #{@credentials_path}"
      # 認証ファイルをクライアント作成時に指定
    elsif ENV['GOOGLE_APPLICATION_CREDENTIALS']
      puts "環境変数のサービスアカウントキーを使用"
      @credentials_path = ENV['GOOGLE_APPLICATION_CREDENTIALS']
    else
      puts "デフォルト認証を使用（gcloud auth application-default login）"
      @credentials_path = nil
    end
  end
    # 接続テスト
  def test_connection
    # プロセッサー情報を取得してみる
    begin
      response = @client.get_processor(name: @processor_name)
      puts "プロセッサー名: #{response.display_name}"
      puts "プロセッサータイプ: #{response.type}"
    rescue => e
      raise "DocumentAI接続テストに失敗: #{e.message}"
    end
  end
end
