#!/usr/bin/env python3
import json
import requests
import base64

# Test the network endpoint
def test_network_endpoint():
    # Sample text for testing
    test_text = """
    Artificial intelligence and machine learning are transforming the technology industry. 
    Deep learning algorithms process vast amounts of data to recognize patterns and make predictions. 
    Neural networks mimic the human brain's structure to solve complex problems. 
    Computer vision enables machines to interpret visual information from the world around them. 
    Natural language processing allows computers to understand and generate human language. 
    These technologies are being applied in healthcare, finance, automotive, and many other sectors. 
    Autonomous vehicles use AI to navigate roads safely. Medical diagnosis systems help doctors detect diseases earlier. 
    Recommendation systems personalize user experiences on digital platforms. 
    Robotics combines AI with mechanical engineering to create intelligent machines.
    """
    
    url = "http://localhost:8766/network"
    payload = {
        "text": test_text,
        "clusters": 5
    }
    
    try:
        print("Testing network endpoint...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            print(f"[CHART] Clusters: {data['clusters']}")
            print(f"📝 Word count: {data['wordCount']}")
            
            if 'image' in data:
                print("🖼️ Network plot image generated successfully!")
                # Save image to file for verification
                img_data = base64.b64decode(data['image'])
                with open('test_network_plot.png', 'wb') as f:
                    f.write(img_data)
                print("💾 Image saved as 'test_network_plot.png'")
            else:
                print("❌ No image in response")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_network_endpoint()
