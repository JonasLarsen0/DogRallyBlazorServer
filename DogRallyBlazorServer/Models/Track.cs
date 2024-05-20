using System.ComponentModel.DataAnnotations;
using System.Drawing;

namespace DogRallyBlazorServer.Models
{
    public class Track
    {
        public int TrackId { get; set; }
        public DateTime Date { get; set; }
        public string PlaceName { get; set; }
        public string CreatorName { get; set; }
        public string JudgeName { get; set; }

        public string TrackImg { get; set; }
        public Class Class { get; set; }
        
    }

    public enum Class
    {
        [Display(Name = "Begynder")]
        Begynderklasse,

        [Display(Name = "Øvet")]
        ØvedeKlasse,

        [Display(Name = "Ekspert")]
        Ekspertklasse,

        [Display(Name = "Champion")]
        Championklasse,

        [Display(Name = "Senior")]
        Seniorklasse
    }
}
