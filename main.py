import requests
import json
import os
import random
import time
import traceback
import re


class MiMotion:
    def __init__(self, check_item):
        self.check_item = check_item
        self.phone = check_item.get("phone")
        self.password = check_item.get("password")
        self.nickname = check_item.get("nickname", self.phone)
        self.min_step = int(check_item.get("min_step", 10000))
        self.max_step = int(check_item.get("max_step", 20000))
        self.token = None
        self.userid = None

    # ---------------- 推送 ----------------
    def push(self, title, content):
        print(f"【酷推推送】{title}\n{content}")

    def push_wx(self, content):
        print(f"【Server酱推送】\n{content}")

    def run(self, content):
        print(f"【企业微信推送】\n{content}")

    # ---------------- 登录逻辑（真实API） ----------------
    def get_token(self):
        """登录获取 token"""
        user = self.phone
        password = self.password
        try:
            print(f"👉 {self.nickname} 正在尝试登录...")

            url1 = f"https://api-user.huami.com/registrations/{user}/tokens"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": "MiFit/4.6.0 (iPhone; iOS 14.0.1; Scale/2.00)",
            }
            data1 = {
                "client_id": "HuaMi",
                "password": f"{password}",
                "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
                "token": "access",
            }

            r1 = requests.post(url=url1, data=data1, headers=headers, allow_redirects=False)
            print('登录响应状态码:', r1.status_code)

            # 429：请求太频繁
            if r1.status_code == 429:
                print("⚠️ 登录过于频繁，等待 5 秒后重试")
                time.sleep(5)
                raise Exception("too many requests")

            location = r1.headers.get("Location")
            if not location:
                print("⚠️ 登录接口未返回 Location，可能是账号密码错误或接口变动")
                return None, None

            code_pattern = re.compile("(?<=access=).*?(?=&)")
            code_matches = code_pattern.findall(location)
            if len(code_matches) > 0:
                code = code_matches[0]
            else:
                print("⚠️ 未找到 access code，登录失败")
                return None, None

            url2 = "https://account.huami.com/v2/client/login"
            if "+86" in user:
                data2 = {
                    "app_name": "com.xiaomi.hm.health",
                    "app_version": "5.0.2",
                    "code": f"{code}",
                    "country_code": "CN",
                    "device_id": "10E2A98F-D36F-4DF1-A7B9-3FBD8FBEB800",
                    "device_model": "phone",
                    "grant_type": "access_token",
                    "third_name": "huami_phone",
                }
            elif "@" in user:
                data2 = {
                    "allow_registration": "false",
                    "app_name": "com.xiaomi.hm.health",
                    "app_version": "6.5.5",
                    "code": f"{code}",
                    "country_code": "CN",
                    "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
                    "device_model": "phone",
                    "dn": "api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com",
                    "grant_type": "access_token",
                    "lang": "zh_CN",
                    "os_version": "1.5.0",
                    "source": "com.xiaomi.hm.health",
                    "third_name": "email",
                }
            else:
                print("⚠️ 用户名格式错误（需为手机号或邮箱）")
                return None, None

            r2 = requests.post(url=url2, data=data2, headers=headers).json()
            self.token = r2["token_info"]["login_token"]
            self.userid = r2["token_info"]["user_id"]
            print(f"✅ {self.nickname} 登录成功，用户ID：{self.userid}")
            return self.token, self.userid

        except Exception as e:
            print(f"❌ 登录失败：{e}")
            return None, None

    # ---------------- 更新步数 ----------------
    def update_step(self, step):
        """上传步数"""
        print(f"📶 正在更新步数到 {step} 步...")
        if not self.token or not self.userid:
            print("⚠️ 缺少 token 或 userid，无法更新步数")
            return

        try:
            url = f"https://api-mifit-cn.huami.com/v1/data/band_data.json?&t={int(time.time())}"
            headers = {
                "User-Agent": "MiFit/6.5.5 (iPhone; iOS 14.0.1; Scale/2.00)",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            }
            data = {
                "data_json": json.dumps({
                    "data_type": 4,
                    "data_source": 2,
                    "source": "com.xiaomi.hm.health",
                    "user_id": self.userid,
                    "device_type": "phone",
                    "summary": {
                        "steps": step
                    }
                })
            }
            r = requests.post(url, headers=headers, data=data)
            if r.status_code == 200:
                print(f"✅ {self.nickname} 步数更新成功！")
            else:
                print(f"⚠️ {self.nickname} 步数更新失败：{r.text}")
        except Exception as e:
            print(f"❌ 更新步数异常：{e}")

    # ---------------- 主逻辑 ----------------
    def main(self):
        """登录 + 更新步数 + 自动重试"""
        for attempt in range(3):
            try:
                token, userid = self.get_token()
                if not token:
                    raise Exception("未获取到token")
                step = random.randint(self.min_step, self.max_step)
                self.update_step(step)
                return f"{self.nickname} 今日步数：{step}\n"
            except Exception as e:
                print(f"⚠️ {self.nickname} 第 {attempt + 1} 次尝试失败：{e}")
                time.sleep(5)
        return f"❌ {self.nickname} 登录或更新步数失败。\n"


# ---------------- 主程序入口 ----------------
if __name__ == "__main__":
    try:
        datas = json.loads(os.environ["CONFIG"])
        msg = ""

        for i in range(len(datas.get("MIMOTION", []))):
            _check_item = datas.get("MIMOTION", [])[i]
            msg += MiMotion(check_item=_check_item).main()

        print("\n=== 执行结果 ===")
        print(msg)

        if datas.get("SKEY"):
            MiMotion(check_item=_check_item).push('【小米运动步数修改】', msg)

        if datas.get("SCKEY"):
            MiMotion(check_item=_check_item).push_wx(msg)

        if datas.get("POSITION"):
            MiMotion(check_item=_check_item).run(msg)

    except Exception as e:
        error_traceback = traceback.format_exc()
        print("❌ 程序异常：")
        print(error_traceback)
