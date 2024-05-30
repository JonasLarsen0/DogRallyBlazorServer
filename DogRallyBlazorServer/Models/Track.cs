using System.ComponentModel.DataAnnotations;
using System.Drawing;
using System.Reflection;

namespace DogRallyBlazorServer.Models
{
    public class Track //Setting the properties for the track.
    {
        public int TrackId { get; set; }
        public DateTime Date { get; set; }
        public string PlaceName { get; set; }
        public string CreatorName { get; set; }
        public string JudgeName { get; set; }
        public RallyClass RallyClass { get; set; }

        //file
        public string? FileName { get; set; }
        public string UserName { get; set; } = "user1";
    }

    public enum RallyClass
    {
        [Display(Name = "Begynder")]
        Beginner,

        [Display(Name = "Øvet")]
        Experienced,

        [Display(Name = "Ekspert")]
        Expert,

        [Display(Name = "Champion")]
        Champion,

        [Display(Name = "Senior")]
        Senior
    }
    public static class EnumExtensions
    {
        public static string? GetDisplayName(this Enum enumValue)
        {
            return enumValue.GetType().GetMember(enumValue.ToString()).First().GetCustomAttribute<DisplayAttribute>()?.GetName();
        }
    }
}
