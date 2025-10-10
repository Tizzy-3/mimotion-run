import requests, json, re, os, traceback, random, time

def login(user, password):
    try:
        print(f"👉 正在尝试登录账号：{user}")
        url1 = f"https://api-user.huami.com/registrations/{user}/tokens"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": "MiFit/6.6.0 (iPhone; iOS 17.0; Scale/3.00)",
        }
        data1 = {
            "client_id": "HuaMi",
            "password": f"{password}",
            "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
            "token": "access",
        }

        r1 = requests.post(url=url1, data=data1, headers=headers, allow_redirects=False)
        print('登录响应状态码:', r1.status_code)
        print('登录响应头:', dict(r1.headers))
        print('登录响应体前500字:', r1.text[:500])

        location = r1.headers.get("Location", "")
        if not location:
            match = re.search(r"https://s3-us-west-2\.amazonaws\.com/hm-registration/successsignin\.html\?access=.*?&", r1.text)
            if match:
                location = match.group(0)
            else:
                print("⚠️ 登录接口未返回 Location，可能账号密码错误或接口调整")
                return None, None

        code_pattern = re.compile("(?<=access=).*?(?=&)")
        code_matches = code_pattern.findall(location)
        if len(code_matches) > 0:
            code = code_matches[0]
        else:
            print("⚠️ 未找到 access code，登录失败")
            return None, None

        url2 = "https://account.huami.com/v2/client/login"
        data2 = {
            "app_name": "com.xiaomi.hm.health",
            "app_version": "6.6.0",
            "code": f"{code}",
            "country_code": "CN",
            "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
            "device_model": "phone",
            "grant_type": "access_token",
            "third_name": "huami_phone" if "+86" in user else "email",
        }

        r2 = requests.post(url=url2, data=data2, headers=headers).json()
        login_token = r2["token_info"]["login_token"]
        userid = r2["token_info"]["user_id"]
        print("✅ 登录成功，获取到 login_token 和 user_id")
        return login_token, userid

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(error_traceback)
        return None, None


class MiMotion:
    def __init__(self, check_item):
        self.check_item = check_item

    def main(self):
        user = self.check_item.get("user")
        password = self.check_item.get("password")
        min_step = int(self.check_item.get("min_step", 5000))
        max_step = int(self.check_item.get("max_step", 25000))
        step = random.randint(min_step, max_step)
        print(f"👉 {user} 目标步数：{step}")

        for attempt in range(3):
            print(f"👉 {user} 正在尝试登录... (第{attempt+1}次)")
            login_token, userid = login(user, password)
            if login_token:
                break
            print(f"⚠️ {user} 第 {attempt+1} 次尝试失败：未获取到token")
            time.sleep(2)
        else:
            return f"❌ {user} 登录或更新步数失败。\n"

        # 更新步数逻辑
        url = "https://api-mifit-cn.huami.com/v1/data/band_data.json"
        headers = {"User-Agent": "MiFit/6.6.0"}
        data = {
            "userid": userid,
            "last_sync_time": 0,
            "data_json": json.dumps({
                "data_type": 4,
                "source": 24,
                "timezone": "8.0",
                "data": [{"date": time.strftime("%Y-%m-%d"), "steps": step}],
            }),
        }
        r = requests.post(url, headers=headers, data=data, params={"t": login_token})
        print(f"更新步数响应: {r.text[:100]}")
        return f"✅ {user} 步数修改成功：{step}\n"


if __name__ == "__main__":
    try:
        datas = json.loads(os.environ["CONFIG"])
        msg = ""
        for i in range(len(datas.get("MIMOTION", []))):
            check_item = datas.get("MIMOTION", [])[i]
            msg += MiMotion(check_item=check_item).main()
        print("\n=== 执行结果 ===")
        print(msg)
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(error_traceback)
