
import os
import shutil

PN = "DeadlineTracker"
PP = "com/example/deadlinetracker"
PK = "com.example.deadlinetracker"

def create_file(path, content):
    full_path = os.path.join(PN, path)
    dir_name = os.path.dirname(full_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())

if os.path.exists(PN):
    shutil.rmtree(PN)

# 1. Настройка SDK
home = os.path.expanduser("~")
sdk_path = os.path.join(home, "AppData", "Local", "Android", "Sdk").replace("\\", "\\\\").replace(":", "\\:")
create_file("local.properties", "sdk.dir=" + sdk_path)

# 2. ОБНОВЛЕНИЕ ДО GRADLE 8.5 (Теперь поддерживает Java 21)
create_file("gradle/wrapper/gradle-wrapper.properties", """
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.5-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
""")

# 3. settings.gradle
create_file("settings.gradle", """
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = '""" + PN + """'
include ':app'
""")

# 4. build.gradle (Корень)
create_file("build.gradle", """
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.2.2'
        classpath 'org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.22'
        classpath 'com.google.devtools.ksp:com.google.devtools.ksp.gradle.plugin:1.9.22-1.0.17'
    }
}
""")

# 5. app/build.gradle
create_file("app/build.gradle", """
apply plugin: 'com.android.application'
apply plugin: 'org.jetbrains.kotlin.android'
apply plugin: 'com.google.devtools.ksp'

android {
    namespace '""" + PK + """'
    compileSdk 34
    defaultConfig {
        applicationId '""" + PK + """'
        minSdk 26
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = '17'
    }
    buildFeatures {
        compose true
    }
    composeOptions {
        kotlinCompilerExtensionVersion '1.5.8'
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.7.0'
    implementation 'androidx.activity:activity-compose:1.8.2'
    implementation platform('androidx.compose:compose-bom:2024.02.00')
    implementation 'androidx.compose.ui:ui'
    implementation 'androidx.compose.material3:material3'
    implementation 'androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0'
    implementation 'androidx.room:room-runtime:2.6.1'
    implementation 'androidx.room:room-ktx:2.6.1'
    ksp 'androidx.room:room-compiler:2.6.1'
}
""")

# 6. Остальные файлы (Манифест и Код)
create_file("gradle.properties", "android.useAndroidX=true\nandroid.nonTransitiveRClass=true\norg.gradle.jvmargs=-Xmx2048m")

create_file("app/src/main/AndroidManifest.xml", """
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="Мой Дедлайн" android:theme="@style/Theme.AppCompat.Light.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""")

create_file("app/src/main/res/values/themes.xml", '<resources><style name="Theme.AppCompat.Light.NoActionBar" parent="android:Theme.Material.Light.NoActionBar"/></resources>')

create_file("app/src/main/java/"+PP+"/Task.kt", "package "+PK+"\nimport androidx.room.*\n@Entity(tableName=\"tasks\")\ndata class Task(@PrimaryKey(autoGenerate=true) val id:Int=0, val title:String, val deadline:Long, val isCompleted:Boolean=false)")
create_file("app/src/main/java/"+PP+"/TaskDao.kt", "package "+PK+"\nimport androidx.room.*\nimport kotlinx.coroutines.flow.Flow\n@Dao\ninterface TaskDao {\n @Query(\"SELECT * FROM tasks ORDER BY isCompleted ASC, deadline ASC\") fun getAll(): Flow<List<Task>>\n @Insert suspend fun insert(t:Task)\n @Update suspend fun update(t:Task)\n @Delete suspend fun delete(t:Task)\n}")
create_file("app/src/main/java/"+PP+"/AppDatabase.kt", "package "+PK+"\nimport androidx.room.*\nimport android.content.Context\n@Database(entities=[Task::class], version=1, exportSchema=false)\nabstract class AppDatabase: RoomDatabase() {\n abstract fun dao(): TaskDao\n companion object {\n  fun get(c:Context) = Room.databaseBuilder(c, AppDatabase::class.java, \"db\").build()\n }\n}")

create_file("app/src/main/java/"+PP+"/MainActivity.kt", """
package """ + PK + """
import android.app.DatePickerDialog
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.style.TextDecoration
import androidx.lifecycle.*
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class TaskViewModel(app: android.app.Application) : AndroidViewModel(app) {
    private val dao = AppDatabase.get(app).dao()
    val tasks = dao.getAll()
    fun add(title: String, date: Long) = viewModelScope.launch { dao.insert(Task(title = title, deadline = date)) }
    fun toggle(t: Task) = viewModelScope.launch { dao.update(t.copy(isCompleted = !t.isCompleted)) }
    fun delete(t: Task) = viewModelScope.launch { dao.delete(t) }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                val vm: TaskViewModel = viewModel()
                val tasks by vm.tasks.collectAsState(initial = emptyList())
                var text by remember { mutableStateOf("") }
                val ctx = LocalContext.current
                
                Column(modifier = Modifier.padding(16.dp).fillMaxSize()) {
                    Text("Мои Дедлайны", style = MaterialTheme.typography.headlineMedium)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        TextField(value = text, onValueChange = { text = it }, label = { Text("Новая задача") }, modifier = Modifier.weight(1f))
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(onClick = {
                            if (text.isNotBlank()) {
                                val cal = Calendar.getInstance()
                                DatePickerDialog(ctx, { _, y, m, d -> 
                                    val target = Calendar.getInstance(); target.set(y, m, d)
                                    vm.add(text, target.timeInMillis)
                                    text = "" 
                                }, cal.get(Calendar.YEAR), cal.get(Calendar.MONTH), cal.get(Calendar.DAY_OF_MONTH)).show()
                            }
                        }) { Text("OK") }
                    }
                    LazyColumn(modifier = Modifier.padding(top = 16.dp)) {
                        items(tasks) { task ->
                            val date = SimpleDateFormat("dd.MM.yyyy", Locale.getDefault()).format(Date(task.deadline))
                            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(12.dp)) {
                                    Checkbox(checked = task.isCompleted, onCheckedChange = { vm.toggle(task) })
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(task.title, textDecoration = if (task.isCompleted) TextDecoration.LineThrough else null)
                                        Text("До: " + date, style = MaterialTheme.typography.bodySmall)
                                    }
                                    IconButton(onClick = { vm.delete(task) }) { Text("❌") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
""")

print("Проект обновлен для работы с Java 21! Откройте его заново в Android Studio.")
